"""Unit tests for washer family routing."""

from backend.services.vendors.mcmaster.washer_subtype import (
    infer_washer_category_id,
    lock_washer_finish_id,
)


def test_ambiguous_washer_defaults_flat():
    assert infer_washer_category_id("M4 washer") == "flat_washer"


def test_lock_washer_family():
    assert infer_washer_category_id("M5 lock washer") == "lock_washer"
    assert infer_washer_category_id("M3 spring washer") == "lock_washer"


def test_fender_washer_family():
    assert infer_washer_category_id("M6 fender washer") == "fender_washer"


def test_lock_finish_prefers_split_socket_for_spring():
    assert lock_washer_finish_id("M5 spring washer") == "split_socket"


def test_lock_finish_general_without_socket_context():
    assert lock_washer_finish_id("M8 lock washer") == "general"
