import copy
import sys
import unittest
from support import ROOT, catalog, workflows

sys.path.insert(0, str(ROOT/'scripts'))
from drama3_presets import presets
from drama3_batch import spoken_text, normalized


class RecipeLibrary:
    def __init__(self, rows):
        self.rows = {r['id']: r for r in rows}
        self.builtin = catalog.Library(user=ROOT/'.generation/export-user')

    def record(self, identifier, kind=None):
        if identifier in self.rows:
            return self.rows[identifier]
        return self.builtin.record(identifier, kind)


class DialogueTests(unittest.TestCase):
    def test_complete_curated_recipe_coverage(self):
        rows=presets()
        self.assertEqual(len(rows),35)
        self.assertEqual(len({r['id'] for r in rows}),35)
        self.assertEqual(sum(r['mode']=='dialogue' for r in rows),6)
        self.assertEqual(sum(r['category']=='whisper' for r in rows),4)
        self.assertEqual(sum(r['category']=='emotion' for r in rows),10)
        for row in rows:
            self.assertIn('text',row)
            self.assertEqual(row['parameters']['generation']['temperature'],1.0)
            if row['mode']=='dialogue':
                self.assertEqual(len(set(row['voice_ids'].values())),2)
                self.assertIn('<|speaker:0|>',row['text'])
                self.assertIn('<|speaker:1|>',row['text'])

    def test_each_recipe_exports_consistent_api_and_connected_ui(self):
        rows=presets();lib=RecipeLibrary(rows)
        for row in rows:
            with self.subTest(id=row['id']):
                api=workflows.export(row['id'],format='api',lib=lib)
                graph=workflows.export(row['id'],language='en',lib=lib)
                by_id={node['id']:node for node in graph['nodes']}
                self.assertEqual(api['1']['inputs']['value'],row['text'])
                for link,origin,slot,target,target_slot,typ in graph['links']:
                    self.assertEqual(by_id[target]['inputs'][target_slot]['link'],link)
                    self.assertEqual(by_id[origin]['outputs'][slot]['type'],typ)
                if row['mode']=='dialogue':
                    self.assertEqual(api['20']['inputs']['voices'],{'voice0':['12',0],'voice1':['13',0]})
                    self.assertEqual(api['12']['inputs']['audio'],['4',0])
                    self.assertEqual(api['13']['inputs']['audio'],['7',0])
                    self.assertEqual(api['13']['inputs']['transcript'],['7',1])
                    self.assertNotEqual(api['4']['inputs']['reference_id'],api['7']['inputs']['reference_id'])
                    self.assertEqual(by_id[4]['pos'][0],by_id[7]['pos'][0])
                    self.assertIn('speaker:1',by_id[40]['widgets_values'][0])
                    self.assertEqual(by_id[7]['widgets_values'][1],'en')

    def test_invalid_or_duplicate_dialogue_cast_is_rejected(self):
        row=copy.deepcopy(next(r for r in presets() if r['mode']=='dialogue'))
        lib=RecipeLibrary([row])
        for cast in [{'voice0':'huola-dachu'}, {'voice0':'huola-dachu','voice1':'huola-dachu'}, {'voice0':'huola-dachu','voice2':'warm-female-zh'}]:
            row['voice_ids']=cast
            with self.assertRaises(catalog.LibraryError): workflows.prompt_for(row,lib=lib)

    def test_reference_recordings_are_actually_different(self):
        lib=RecipeLibrary([]).builtin
        self.assertNotEqual(lib.record('huola-dachu')['sha256'],lib.record('warm-female-zh')['sha256'])
        self.assertNotEqual(lib.asset('huola-dachu').read_bytes(),lib.asset('warm-female-zh').read_bytes())

    def test_asr_expected_text_excludes_directions_and_speaker_markup(self):
        text='Direction: whisper softly.\nLine: 你好。<whisper>听我说。</whisper>'
        self.assertEqual(normalized(text),'你好听我说')
        self.assertEqual(normalized('<|speaker:0|> [sighs] 别怕。\n<|speaker:1|> 好的。'),'别怕好的')
