import pytest

from roboduck import logging, DummyChatModel


def test_exception_logging(capfd):
    logger = logging.getLogger('test', chat_class=DummyChatModel)
    # Intentionally raise an error.
    try:
        x = [][2]
        error_message = ''
    except Exception as e:
        logger.error(e)
        error_message = str(e)
    out, _ = capfd.readouterr()

    # Dummy model just returns uppercase version of prompt.
    assert 'INDEXERROR: LIST INDEX OUT OF RANGE' in out
    assert 'NATURAL LANGUAGE ANSWER' in out
    assert error_message in out


def test_stdout_logging(capfd):
    logger = logging.DuckLogger('test', chat_class=DummyChatModel)
    logger.warning('this is a warning')
    out, _ = capfd.readouterr()
    assert 'this is a warning' in out


def test_no_stdout_logging(tmp_path, capfd):
    logger = logging.DuckLogger('test', chat_class=DummyChatModel,
                                stdout=False, path=tmp_path/'test.log')
    logger.warning('this is a warning')
    out, _ = capfd.readouterr()
    assert not out


def test_file_logging(tmp_path, capfd):
    log_file = tmp_path/'test.log'
    logger = logging.getLogger('test', path=log_file, stdout=False,
                               chat_class=DummyChatModel)
    logger.info('test message')
    try:
        z = 3 + 'a'
    except Exception as e:
        logger.error(e)
    logged_msg = log_file.read_text().strip()
    out, _ = capfd.readouterr()

    # Dummy model just returns uppercase version of prompt.
    assert 'TYPEERROR: UNSUPPORTED OPERAND TYPE(S) FOR +:' in logged_msg
    # Note: if we make this function much bigger or make our prompt much
    # longer, we could run into issues here where our DuckDB class will raise a
    # warning, thus polluting stdout and breaking the test below. But in our
    # current state this should be fine.
    assert not out.strip()


def test_logger_requires_at_least_one_handler():
    with pytest.raises(RuntimeError):
        logger = logging.getLogger('test', stdout=False, path='')
