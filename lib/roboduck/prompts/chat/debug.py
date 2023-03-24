"""TODO: add any relevant docs here.
"""

# COMPLETION KWARGS
kwargs = {
    'temperature': 0.0,
    'top_p': .99,
    'max_length': 512,
    'frequency_penalty': 0.2,
    'presence_penalty': 0.0,
    'logit_bias': {
        37811: -100,
        27901: -50,
    },
    'stop': [
        'QUESTION',
        'SOLUTION PART 1',
        'SOLUTION PART 2',
    ]

}

# SYSTEM MESSAGE (str)
system = """You are an incredibly effective AI programming assistant. You have in-depth knowledge across a broad range of sub-fields within computer science, software development, and data science, and your goal is to help Python programmers resolve their most challenging bugs."""

# USER MESSAGES (str or dict)
# If dict, first key is default.
_contextful_prompt = """
This code snippet is not working as expected. Help me debug it. First read my question, then examine the snippet of code that is causing the issue and look at the values of the local and global variables. Your response must have exactly two parts. In the section titled SOLUTION PART 1, use plain English to explain what the problem is and how to fix it (if you don't know what the problem is, SOLUTION PART 1 should instead list a few possible causes or things I could try in order to identify the issue). In the section titled SOLUTION PART 2, write a corrected version of the input code snippet (if you don't know, SOLUTION PART 2 should say None). SOLUTION PART 2 must contain only python code - there must not be any English explanation outside of code comments or docstrings. Be concise and use simple language because I am a beginning programmer.

QUESTION:
{question}

CURRENT CODE SNIPPET:
{code}

NEXT LINE:
{next_line}

LOCAL VARIABLES:
{local_vars}

GLOBAL VARIABLES:
{global_vars}
""".strip()
_contextless_prompt = """
QUESTION:
{question}
""".strip()
user = {
    'contextful': _contextful_prompt,
    'contextless': _contextless_prompt,
}