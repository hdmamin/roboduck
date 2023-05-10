Roboduck provides prompts for interactive debugging and stack trace analysis, but you can also define your own. This involves a few steps:

1. **Construct a prompt template.**  
Roboduck defines prompt templates using yaml files. You can find an example [here](https://github.com/hdmamin/roboduck/tree/main/lib/roboduck/prompts/chat). The kwargs are passed to langchain and correspond to common model hyperaparameters you can find in the openai api docs. Roboduck typically defines two types of user messages: first is the default message type (called "contextful" in the example linked above) which is used whenever program state has changed since the user's last question. The second ("contextless" in our example) is used when state has not changed, e.g. when asking a followup question during an interactive debugging session. You can create a similar yaml file locally containing whatever instructions you want to show the model. We expect model output to consist of a natural language explanation followed by an optional code snippet - it's technically possible to override this expectation by writing a custom replacement for roboduck's `utils.parse_completion` function, but we don't anticipate that being a common workflow.

2. **[Optional] Subclass `roboduck.DuckDB` and implement a custom `_get_prompt_kwargs` method.**  
If your custom prompt expects different fields than our default prompt, you need to provide the debugger with a way to access them. `_get_prompt_kwargs` must return a dictionary with values for all of these fields. You can find roboduck's default implementation [here](https://github.com/hdmamin/roboduck/blob/fb2c7865c6435812d44d2df8fa12d53d7776d73d/lib/roboduck/debug.py#L200). If your prompt contains the same fields and merely changes the instruction wording, you can skip this step.

3. **Specify desired `prompt_name`.**  
Use your custom template as follows:

```
# In a debugger:
from roboduck import duck

duck(prompt_name=your_template_path)
```

```
# In a logger:
from roboduck import logging

logger = logging.getLogger(prompt_name=your_template_path)
```

```
# In error explanation mode:
from roboduck import errors

errors.enable(prompt_name=your_template_path)
```
