import unittest

from windprofiel.preview import standalone_html


class PreviewTests(unittest.TestCase):
    def test_standalone_assets_embedded_and_script_data_escaped(self):
        # Geen productiedata: deze fixture controleert alleen de HTML-export.
        profiles = {"2025-06-01": {"description": "</script><script>danger</script>"}}
        html = standalone_html(profiles)
        self.assertIn('value="2025-06-01"', html)
        self.assertIn("window.WINDPROFIEL_PREVIEW=", html)
        self.assertNotIn("/opsplitsing", html)   # werkt alleen met de server
        self.assertNotIn('src="./app.js"', html)
        self.assertNotIn('href="./style.css"', html)
        self.assertNotIn("</script><script>danger</script>", html)
        self.assertIn("\\u003c/script>", html)
