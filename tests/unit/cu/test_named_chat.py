from dodaios.cu.named_chat import selected_chat_matches


def read(node, key):
    return node.get(key)


def test_visible_unselected_chat_title_is_not_target_proof():
    root = {"AXChildren": [{"AXTitle": "Jarvis Test", "AXSelected": False}]}
    assert not selected_chat_matches(root, "Jarvis Test", read)


def test_exact_selected_chat_is_target_proof():
    root = {"AXChildren": [{"AXSelected": True, "AXChildren": [{"AXTitle": "Jarvis Test"}]}]}
    assert selected_chat_matches(root, "Jarvis Test", read)
    assert not selected_chat_matches(root, "Jarvis", read)


def test_different_or_unreadable_selection_is_refused():
    root = {"AXChildren": [{"AXTitle": "Other chat", "AXSelected": True}, {"AXTitle": "Jarvis Test"}]}
    assert not selected_chat_matches(root, "Jarvis Test", read)
    assert not selected_chat_matches({}, "Jarvis Test", read)
