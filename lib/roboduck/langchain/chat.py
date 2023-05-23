"""Functionality related to langchain chat models. This includes both a wrapper
class `Chat` that makes it easier to load and use multiple user reply types
from a config file as well as ChatModel replacements (i.e. instead of
ChatOpenAI).
"""
from functools import partial
from langchain.callbacks.base import CallbackManager
from langchain.chat_models import ChatOpenAI
from langchain.schema import ChatResult, ChatGeneration, AIMessage, \
    SystemMessage
from langchain.prompts import HumanMessagePromptTemplate
import warnings

from roboduck.config import apply_config_defaults
from roboduck.decorators import add_kwargs
from roboduck.langchain.callbacks import LiveTypingCallbackHandler
from roboduck.langchain.utils import model_context_window
from roboduck.prompts.utils import load_template


class DummyChatModel:
    # Drop-in replacement for ChatOpenAI that just repeats the last message.
    # We'd have to be a bit more rigid about expects init args if we want to
    # subclass from BaseChatModel. For now this is fine.

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
        self.verbose = getattr(self, 'verbose', True)

    def __call__(self, messages, stop=None):
        return self._generate(messages, stop=stop).generations[0].message

    def _generate(self, messages, stop=None):
        if stop:
            warnings.warn(
                f'`stop` param is ignored by {type(self).__name__}. You '
                f'specified stop={stop}.'
            )
        res = messages[-1].content.upper()
        if self.streaming:
            tokens = [tok + ' ' for tok in res.split(' ')]
            tokens[-1] = tokens[-1].rstrip(' ')
            for token in tokens:
                self.callback_manager.on_llm_new_token(
                    token,
                    verbose=self.verbose,
                )
        message = AIMessage(content=res)
        return ChatResult(generations=[ChatGeneration(message=message)])

    async def _agenerate(self, messages, stop=None):
        warnings.warn(
            f'{type(self).__name__} doesn\'t provide a real _agenerate '
            'method. Calling synchronous generate() instead.'
        )
        return self._generate(messages, stop=stop)


class Chat:
    """Convenience class to make it easier to interact with chat model via
    langchain. Allows you to specify reply types and kwargs via config, avoid
    manually tracking the conversation history, etc.

    We recommend instantiating via the from_template factory method in most
    cases.
    """

    def __init__(self, system, user, chat_class=ChatOpenAI,
                 history=(), streaming=True, **kwargs):
        r"""
        Parameters
        ----------
        system : str
            "system" message for chatGPT. This typically contains instructions
            for how GPT should behave when talking to the user.
        user : str or dict
            Defines one or more types of "user" messages for chatGPT. If you
            have multiple types, the keys in your dict will be used to
            define methods, so name them accordingly. E.g. if you pass in a
            dict with keys "question" and "comment", you will be able to call
            chat.comment(**kwargs) and chat.question(**kwargs).
        chat_class : type
            The class (usually provided by langchain) that represents the chat
            model we'll be conversing with.
        history : listlike
            This will be used to store all the messages in our conversation.
            If not empty, it should contain AIMessage and HumanMessage objects
            from a previous chat, but NOT a SystemMessage.
        streaming : bool
            Determines whether to query the chat model in streaming mode.
            This is often desirable so that we can see incremental results
            instead of waiting for the whole completion to finish.
        kwargs : any
            Additional kwargs for chat_class. This can include both
            model_kwargs like temperature or top_p that affect completion
            directly, or other miscellaneous kwargs like `callback_manager`
            or `verbose`.

        Examples
        --------
        ```
        # Instantiate from builtin roboduck debugging prompt template (see
        # roboduck.prompts.chat.debug).
        chat = Chat.from_template('debug')
        message = chat.reply(
            code='a = 3\nb = ([0, 1], [2, 3])\nb[1].append(a)',
            question='I thought tuples were immutable. Why doesn\'t appending '
                     'a throw an error?',
            local_vars='{"a": 3, "b": ([0, 1], [2, 3])}',
            global_vars='{"x": True}', next_line='b[1].append(a)'
        )

        # User asks a followup question. The debug prompt template provides
        # multiple user response types ('contextful' and 'contextless')
        # depending on whether the program state needs to be provided (helpful
        # when used in a live debugging session). That's not the case here, so
        # we can use the auto-generated `contextless` method (remember, this
        # depends on the keys you provide via the `user` arg in the
        # constructor). You could also call this like
        # chat.reply(question=question, key_='contextless').
        message = chat.contextless(
            question='Could you expand on the part of your explanation where '
            'you said...'
        )
        ```
        """
        self.kwargs = dict(kwargs)
        self.kwargs.update(streaming=streaming)
        apply_config_defaults(self.kwargs, template_only=False)
        if streaming and 'callback_manager' not in self.kwargs:
            self.kwargs['callback_manager'] = CallbackManager(
                [LiveTypingCallbackHandler()]
            )
        self.chat = chat_class(**self.kwargs)
        self.context_window = model_context_window(
            self.kwargs.get('model_name')
        )
        # This is approximate and counts words, not tokens. It is soft in the
        # sense that it marks not where the user exceeds the model's context
        # window, but where it's long enough that the context window will be a
        # bigger limiting factor than the max_tokens kwarg.
        self.prompt_words_soft_limit = int(
            0.75 * (self.context_window - self.kwargs.get('max_tokens', 0))
        )
        self.prompt_words_hard_limit = int(0.75 * self.context_window)

        # Create system and user messages and templates.
        self.system_message = SystemMessage(content=system)
        if isinstance(user, str):
            user = {'reply': user}
        self.user_templates = {
            k: HumanMessagePromptTemplate.from_template(v)
            for k, v in user.items()
        }
        self.default_user_key = next(iter(self.user_templates))
        self.default_user_fields = (self.user_templates[self.default_user_key]
                                    .input_variables)
        self._history = list(history) or [self.system_message]
        self._create_reply_methods()

    def _create_reply_methods(self):
        """Creates two options for user to send replies:
        1. call chat.reply(), using the key_ arg to determine which type of
        user_message is sent. The docstring shows the default user
        message type's fields but if you set the key accordingly you can pass
        in fields for another message type.
        2. call methods like chat.question() or chat.statement(), where 'chat'
        and 'statement' are the names of all available user message types
        (i.e. the keys of the `user` dict in the prompt config file). You can
        not pass in key_.
        """
        for k, v in self.user_templates.items():
            if hasattr(self, k):
                warnings.warn(
                    f'Name collision: prompt defines user message type {k} '
                    f'but Chat class already has a method with that name. '
                    f'Method will be named {k}_ instead.'
                )
                k = k + '_'
            meth = add_kwargs(partial(self._reply, key_=k),
                              fields=v.input_variables,
                              hide_fields=['key_'],
                              strict=True)
            setattr(self, k, meth)
        setattr(
            self,
            'reply',
            add_kwargs(self._reply, self.default_user_fields, strict=False)
        )

    @classmethod
    def from_template(cls, name, **kwargs):
        """Instantiate a Chat object from a yaml template (either builtin
        roboduck prompt templates like in roboduck.prompts.chat or a user
        defined file with the same format).

        Parameters
        ----------
        name : str
            Name of a builtin roboduck prompt template
            (see roboduck.prompts.utils.available_templates()) or a file
            containing a user-defined prompt template.
        kwargs : any
            Additional kwargs to pass to constructor. These take precedence
            over the config file if their is a collision, i.e. the config
            provides the defaults but you can override them.

        Returns
        -------
        Chat
        """
        template = load_template(name)
        # Important that we call this BEFORE taking user kwargs into account.
        # Init will handle the resolution that occurs afterwards, do not make
        # a second call to apply defaults in this method.
        apply_config_defaults(template['kwargs'], template_only=True)
        if kwargs:
            template['kwargs'].update(kwargs)
        kwargs = template.pop('kwargs', {})
        return cls(**template, **kwargs)

    def user_message(self, *, key_='', **kwargs):
        """Get a fully resolved user reply as a string.

        Parameters
        ----------
        key_ : str
            Determines which reply type to use. If empty, falls back to default
            reply type.
        kwargs : str
            The required fields for the selected reply type.

        Returns
        -------
        str
        """
        key = key_ or self.default_user_key
        template = self.user_templates[key]
        return template.format(**kwargs)

    def _reply(self, *, key_='', **kwargs):
        """The basic functionality that will underlie the dynamically generated
        `reply` method and its other aliases. Passes user reply and
        conversational history to an LLM for a response.

        Parameters
        ----------
        key_: str
            Determines which type of user reply to use. Defaults to the first
            type defined in the prompt config.
        kwargs: any
            Fields expected by the relevant user prompt type. These will be
            injected into the docstrings of our dynamically generated methods.

        Returns
        -------
        AIMessage
        """
        user_message = self.user_message(key_=key_, **kwargs)
        self._history.append(user_message)
        self._truncate_history()
        try:
            response = self.chat(self._history)
        except Exception as e:
            self._history.pop(-1)
            raise e
        self._history.append(response)
        return response

    def history(self, sep='\n\n', speaker_prefix=True):
        """Return chat history as a single string.

        Parameters
        ----------
        sep : str
            Character(s) used to separate conversational turns in the output.
            The default leaves 1 blank line between each turn.
        speaker_prefix : bool
            If True, preprend each turn with "Human" or "AI" depending on the
            speaker.

        Returns
        -------
        str
        """
        res = []
        for row in self._history:
            reply = row.content
            if speaker_prefix:
                speaker = type(row).__name__.split('Message')[0]
                reply = f'{speaker}: {reply}'
            res.append(reply)
        return sep.join(res)

    def input_variables(self, key=''):
        """Get names of fields that user has to pass in when replying.

        Parameters
        ----------
        key : str
            Name of user reply type. Falls back to the default reply type if
            none is provided.

        Returns
        -------
        set[str]
        """
        template = self.user_templates[key or self.default_user_key]
        return set(template.input_variables)

    def _truncate_history(self):
        """Dynamically discard old turns until our history is an
        acceptable size for our LLM's context window. Operates in place. Called
        automatically by _reply.
        """
        # Technically I don't think this is the exact prompt that gets sent
        # but it's close enough for our estimate. We're doing some pretty rough
        # arithmetic anyway with the token->word conversions.
        n_words = len(self.history(sep='\n').split())
        while n_words > self.prompt_words_hard_limit:
            if len(self._history) <= 2:
                raise ValueError(
                    f'Chat history contains ~{n_words:,} words even when only '
                    f'including the system prompt and the latest user message,'
                    f' which is more than this model can support. Context '
                    f'window is ~{self.prompt_words_hard_limit:,} words '
                    f'({self.context_window:,} tokens). You could try using '
                    f'a different model_name with a larger context window, a '
                    f'prompt_name corresponding to a more concise prompt, '
                    f'a smaller max_len_per_var (default is 79), or '
                    f'refactoring your code (this error could potentially be '
                    f'caused by a truly enormous function).'
                )
            turn = self._history.pop(1)
            # Subtract an extra 1 for the speaker prefix. This is an
            # approximate calculation regardless so it doesn't really matter
            # but it also shouldn't hurt.
            n_words = n_words - len(turn.content.split()) - 1

        if n_words > self.prompt_words_soft_limit:
            warnings.warn(
                f'Chat history contains ~{n_words:,} words which means the '
                f'model\'s context window of ~{self.prompt_words_hard_limit:,}'
                f' words ({self.context_window:,} tokens) will be the '
                'bigger limiting factor than your max_length hyperparameter.'
            )
