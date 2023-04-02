from langchain.schema import ChatResult, ChatGeneration, AIMessage
import warnings

from roboduck.langchain.callbacks import LiveTypingCallbackHandler


class DummyChatModel:
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