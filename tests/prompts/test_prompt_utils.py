"""File name must differ from tests/test_utils.py to avoid pytest error.

"""
from pathlib import Path
import pytest

from roboduck.prompts import utils


def test_available_templates():
    all_templates = utils.available_templates()
    assert sorted(all_templates) == ['chat', 'completion']
    assert 'debug' in all_templates['chat']

    chat_templates = utils.available_templates('chat')
    assert chat_templates == all_templates['chat']


def test_load_template():
    template = utils.load_template('debug')
    assert isinstance(template, dict)
    assert 'model_name' in template['kwargs']
    assert 'temperature' in template['kwargs']

    # Load same template from path.
    repo_root = Path(__file__).parent.parent.parent
    template_2 = utils.load_template(
        repo_root/'lib/roboduck/prompts/chat/debug.yaml'
    )
    assert template_2 == template