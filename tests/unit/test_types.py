from typing import cast
from spectacles.types import QueryResult, QueryError, ErrorQueryResult
from pydantic import ValidationError
import pytest


def test_message_and_message_details_are_concatenated():
    message = "An error ocurrred."
    message_details = "We were unable to look up the query requested."
    error = QueryError(
        message=message, message_details=message_details, sql_error_loc=None
    )
    assert error.full_message == message + " " + message_details


def test_extract_error_details_error_other():
    response_json = {"status": "error", "data": "some string"}
    with pytest.raises(ValidationError):
        QueryResult.parse_obj(response_json)


def test_extract_error_details_should_error_on_non_str_message_details():
    response_json = {
        "status": "error",
        "data": {
            "id": "abcdef12345",
            "runtime": 1.0,
            "errors": [
                {
                    "message_details": {
                        "message": "An error messsage.",
                        "details": "More details.",
                    }
                }
            ],
            "sql": "SELECT * FROM orders",
        },
    }
    with pytest.raises(ValidationError):
        QueryResult.parse_obj(response_json)


def test_query_results_with_no_message_details_works():
    message = "An error message."
    response_json = {
        "status": "error",
        "data": {
            "id": "abcdef12345",
            "runtime": 1.0,
            "errors": [{"message": message, "message_details": None}],
            "sql": "SELECT * FROM orders",
        },
    }
    query_result = cast(ErrorQueryResult, QueryResult.parse_obj(response_json).__root__)
    valid_errors = query_result.get_valid_errors()
    assert valid_errors[0].message == message
    assert valid_errors[0].full_message == message


def test_query_results_sql_loc_character_only_works():
    message = "An error message."
    sql = "SELECT x FROM orders"
    response_json = {
        "status": "error",
        "data": {
            "id": "abcdef12345",
            "runtime": 1.0,
            "errors": [{"message": message, "sql_error_loc": {"character": 8}}],
            "sql": sql,
        },
    }
    assert QueryResult.parse_obj(response_json)


def test_get_valid_errors_should_return_errors():
    # The current version of this warning message text
    error_message = "An error message."
    warning_message = (
        "Note: This query contains derived tables with Development Mode filters. "
        "Query results in Production Mode might be different."
    )
    sql = "SELECT x FROM orders"
    response_json = {
        "status": "error",
        "data": {
            "id": "abcdef12345",
            "runtime": 1.0,
            "errors": [
                {"message": warning_message},
                {"message": error_message, "sql_error_loc": {"character": 8}},
            ],
            "sql": sql,
        },
    }
    query_result = cast(ErrorQueryResult, QueryResult.parse_obj(response_json).__root__)
    valid_errors = query_result.get_valid_errors()
    assert valid_errors
    assert valid_errors[0].message == error_message
    assert query_result.sql == sql


def test_get_valid_errors_should_ignore_warnings():
    # The current version of this warning message text
    warning_message = (
        "Note: This query contains derived tables with Development Mode filters. "
        "Query results in Production Mode might be different."
    )
    sql = "SELECT x FROM orders"
    response_json = {
        "status": "error",
        "data": {
            "id": "abcdef12345",
            "runtime": 1.0,
            "errors": [{"message": warning_message}],
            "sql": sql,
        },
    }
    query_result = cast(ErrorQueryResult, QueryResult.parse_obj(response_json).__root__)
    valid_errors = query_result.get_valid_errors()
    assert not valid_errors

    # This is the original version of this warning message text.
    # Some users with older Looker instances might still get this one.
    warning_message = (
        "Note: This query contains derived tables with conditional SQL for Development Mode. "
        "Query results in Production Mode might be different."
    )
    response_json["data"]["errors"][0]["message"] = warning_message
    query_result = cast(ErrorQueryResult, QueryResult.parse_obj(response_json).__root__)
    valid_errors = query_result.get_valid_errors()
    assert not valid_errors


def test_can_parse_string_errors():
    response = {
        "status": "error",
        "result_source": None,
        "data": {
            "from_cache": True,
            "id": "67120bd3c7d23eb81f72692be9581c4a",
            "error": "View Not Found",
        },
    }

    result = QueryResult.parse_obj(response).__root__
    assert isinstance(result, ErrorQueryResult)
    assert result.errors[0].message == "View Not Found"
    assert result.runtime == 0.0
    assert result.sql == ""
