import pytest

from app import befaehigungen as bf


def test_selection_and_header():
    areas = bf.parse_selection([
        {"num": "VI", "unterpunkte": [{"idx": 0, "items": [0, 2]}, {"idx": 2, "items": []}], "notes": "10. SJ"},
        {"num": "I", "unterpunkte": [{"idx": 0, "items": [1]}], "lp21": "Personale Kompetenzen – Selbstreflexion"},
    ])
    assert [a["num"] for a in areas] == ["I", "VI"]  # Katalogreihenfolge
    assert areas[1]["unterpunkte"][1]["items"] == bf.CATALOGUE[5]["unterpunkte"][2]["items"]  # leer = alle
    header = bf.build_header(areas)
    assert "[x] I Sich selbst sein und werden" in header and "[x] VI Dranbleiben und bewältigen" in header
    assert header.count("[ ]") == 4
    assert "Dranbleiben und bewältigen – Selbstständigkeit, Flexibilität" in header


def test_selection_errors():
    with pytest.raises(bf.SelectionError):
        bf.parse_selection([])
    with pytest.raises(bf.SelectionError):
        bf.parse_selection([{"num": "I", "unterpunkte": []}])
    four = [{"num": n, "unterpunkte": [{"idx": 0}]} for n in ("I", "II", "III", "IV")]
    with pytest.raises(bf.SelectionError):
        bf.parse_selection(four)


def test_assemble_uses_catalogue_verbatim_and_validates_lp21():
    area = bf.parse_selection([{"num": "I", "unterpunkte": [{"idx": 0, "items": [1, 2]}]}])[0]
    parts = bf.parse_area_output("AUSGANGSLAGE:\nGrund.\nLP21:\nSelbstempfinden\nWAS:\nBezug.\nWO:\nKontext.")
    block = bf.assemble_area(1, area, parts)
    assert block.startswith("### 1 Sich selbst sein und werden\nWOZU:\nGrund.")
    assert "Selbstempfinden – sich selbst wahrnehmen\n- Den Körper als ein zusammengehörendes Ganzes erleben" in block
    assert bf.LP21_PLACEHOLDER in block  # «Selbstempfinden» ist kein LP21-Begriff
    assert block.index("WAS (Bezug LP21):") < block.index("WO – In welchem Kontext")


def test_area_prompt_puts_notes_last():
    area = bf.parse_selection([{"num": "VI", "unterpunkte": [{"idx": 0}], "notes": "Backen am Donnerstag"}])[0]
    msgs = bf.build_area_messages(area=area, student={"first_name": "Kai"}, period="", general_notes="",
                                  student_context="Alter Bericht", kb_context="")
    user = msgs[-1]["content"]
    assert user.index("Alter Bericht") < user.index("=== AUFTRAG ===") < user.index("Backen am Donnerstag")


def test_parse_keeps_only_first_variant():
    text = ("AUSGANGSLAGE:\nErste Variante.\nWAS:\nBezug eins.\nWO:\nKontext eins.\n\n"
            "AUSGANGSLAGE:\nZweite Variante.\nWAS:\nBezug zwei.\nWO:\nKontext zwei.")
    parts = bf.parse_area_output(text)
    assert parts["AUSGANGSLAGE"] == "Erste Variante."
    assert parts["WAS"] == "Bezug eins." and parts["WO"] == "Kontext eins."


def test_prompt_contains_today_and_recency_rule():
    from app.prompts import today_text

    area = bf.parse_selection([{"num": "VI", "unterpunkte": [{"idx": 0}]}])[0]
    user = bf.build_area_messages(area=area, student={"first_name": "Kai", "class_name": "10. SJ"}, period="",
                                  general_notes="", student_context="", kb_context="")[-1]["content"]
    assert f"Heutiges Datum: {today_text()}" in user and "Klasse/Stufe: 10. SJ" in user
    assert "veralteten Angaben" in user
