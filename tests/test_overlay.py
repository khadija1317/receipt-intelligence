from PIL import Image

from src import overlay


def one_box(conf):
    return [{"box": [[50, 50], [150, 50], [150, 100], [50, 100]], "text": "X", "conf": conf}]


def test_confidence_thresholds():
    assert overlay.conf_color(0.80) == overlay.GREEN
    assert overlay.conf_color(0.79) == overlay.ORANGE
    assert overlay.conf_color(0.40) == overlay.ORANGE
    assert overlay.conf_color(0.39) == overlay.RED


def test_box_edge_gets_the_colour_of_its_confidence():
    for conf, color in ((0.95, overlay.GREEN), (0.6, overlay.ORANGE), (0.1, overlay.RED)):
        image = Image.new("RGB", (400, 200), "white")
        drawn = overlay.draw_boxes(image, one_box(conf))
        assert drawn.getpixel((100, 50)) == color  # middle of the top edge


def test_original_image_is_not_modified():
    image = Image.new("RGB", (400, 200), "white")
    overlay.draw_boxes(image, one_box(0.95))
    assert image.getpixel((100, 50)) == (255, 255, 255)


def test_no_pieces_returns_a_same_size_copy():
    image = Image.new("RGB", (400, 200), "white")
    drawn = overlay.draw_boxes(image, [])
    assert drawn.size == (400, 200)
    assert drawn is not image
