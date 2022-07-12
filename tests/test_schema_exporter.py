import logging
import os

from linkml.utils.schema_builder import SchemaBuilder
from linkml.utils.schema_fixer import SchemaFixer
from linkml_runtime.dumpers import yaml_dumper
from linkml_runtime.linkml_model import TypeDefinition
from linkml_runtime.utils.schemaview import SchemaView, SchemaDefinition, SlotDefinition
from schemasheets.schema_exporter import SchemaExporter
from schemasheets.schemamaker import SchemaMaker
from schemasheets.schemasheet_datamodel import SchemaSheet

ROOT = os.path.abspath(os.path.dirname(__file__))
INPUT_DIR = os.path.join(ROOT, 'input')
OUTPUT_DIR = os.path.join(ROOT, 'output')
SHEET = os.path.join(INPUT_DIR, 'personinfo.tsv')
ROUNDTRIPPED_SHEET = os.path.join(OUTPUT_DIR, 'personinfo-roundtrip.tsv')
MINISHEET = os.path.join(OUTPUT_DIR, 'mini.tsv')
TEST_SPEC = os.path.join(INPUT_DIR, 'test-spec.tsv')
ENUM_SPEC = os.path.join(INPUT_DIR, 'enums.tsv')
TYPES_SPEC = os.path.join(INPUT_DIR, 'types.tsv')

EXPECTED = [
    {
        'field': 'id',
        'key': 'True',   ## TODO: should be mapped to 'Yes'
        'range': 'string',
        'desc': 'any identifier',
        'schema.org': 'identifier',
        ## TODO
        ##  'multiplicity': '1',
    },
    {
        'record': 'Person',
        'field': 'age',
        'range': 'decimal',
        'desc': 'age in years'
    },
    {
        'record': 'ForProfit',
        'parents': 'Organization'
    },
    {
        'field': 'name'
    },
    # tests curie contraction
    {
         'record': 'Person',
         'field': 'id',
         'key': 'True',
         'range': 'string',
         'desc': 'identifier for a person',
         'schema.org': 'identifier'
    },
]


def test_roundtrip_schema():
    """
    Tests linkml2sheets by roundtripping from the standard personinfo schema in YAML
    """
    sm = SchemaMaker()
    # sheets2linkml, from SHEET
    schema = sm.create_schema(SHEET)
    exporter = SchemaExporter(schemamaker=sm)
    sv = SchemaView(schema)
    # linkml2sheets, using original sheets as specification
    # (note that this ignores the main data in the TSV)

    exporter.export(sv, specification=SHEET, to_file=ROUNDTRIPPED_SHEET)
    for row in exporter.rows:
        logging.info(row)
    for record in EXPECTED:
        assert record in exporter.rows


def _roundtrip(schema: SchemaDefinition, specification: str):
    sm = SchemaMaker()
    exporter = SchemaExporter(schemamaker=sm)
    sv = SchemaView(schema)
    exporter.export(schemaview=sv, specification=specification, to_file=MINISHEET)
    for row in exporter.rows:
        print(row)
    schema2 = sm.create_schema(MINISHEET)
    sv2 = SchemaView(schema2)
    for e in sv.all_elements().values():
        e2 = sv2.get_element(e.name)
        if e2 is None:
            raise ValueError(f"Could not find {e}")
        e2.from_schema = e.from_schema
        #print(f"Comparing:\n - {e}\n - {e2}")
        for s, v in vars(e).items():
            v2 = getattr(e2, s, None)
            if v != v2:
                logging.error(f"   {s}: {v} ?= {v2}")
            assert v == v2


def test_dynamic():
    """
    tests dynamically building up a schema and exporting
    """
    sb = SchemaBuilder()
    sf = SchemaFixer()
    sb.add_class('A', [])
    sb.add_class('M1', [])
    sb.add_class('M2', [])
    sb.add_class('X', ['s1', 's2'], description='d1', is_a="A", mixins=["M1"])
    sb.add_class('Y', ['s1', 's2'], description='d2', is_a="A", mixins=["M1", "M2"])
    sb.add_slot(SlotDefinition('s1', title="ts1", description='s1', range="Y"))
    sb.add_defaults()
    schema = sb.schema
    _roundtrip(schema, TEST_SPEC)


def test_enums():
    """
    tests a specification that is dedicated to enums
    """
    sb = SchemaBuilder()
    sb.add_enum('E', ['V1', 'V2'])
    sb.add_defaults()
    schema = sb.schema
    # TODO: add this functionality to SchemaBuilder
    e = schema.enums['E']
    e.description = 'test desc'
    #print(yaml_dumper.dumps(schema))
    _roundtrip(schema, ENUM_SPEC)


def test_types():
    """
    tests a specification that is dedicated to types
    """
    sb = SchemaBuilder()
    #sb.add_defaults()
    schema = sb.schema
    # TODO: add this functionality to SchemaBuilder
    t = TypeDefinition('MyString', description='my string', typeof='string')
    schema.types[t.name] = t
    #print(yaml_dumper.dumps(schema))
    _roundtrip(schema, TYPES_SPEC)


def test_spec():
    """
    Tests parsing of specification rows from TSV
    """
    schemasheet = SchemaSheet.from_csv(TEST_SPEC)
    table_config = schemasheet.table_config
    #for c in table_config.columns.values():
    #    print(c)
    mixins_config = table_config.columns["mixins"]
    #print(mixins_config)
    assert "|" == mixins_config.settings.internal_separator


