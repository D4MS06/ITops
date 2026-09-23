from monitoring.storage.mariadb_bootstrap import MariaDBBootstrapper


def test_legacy_custom_service_text_repair_restores_utf8_list_option():
    assert MariaDBBootstrapper._repair_legacy_utf8_mojibake("Mat\u00c3\u00a9riel informatique") == "Matériel informatique"


def test_legacy_custom_service_text_repair_keeps_correct_accented_text():
    assert MariaDBBootstrapper._repair_legacy_utf8_mojibake("Réception complète") == "Réception complète"
