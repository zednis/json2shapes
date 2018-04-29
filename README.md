# json2shapes

## Dependencies

Running these scripts requires python3+.  For information on installing Python, visit the [Python Beginners Guide](https://wiki.python.org/moin/BeginnersGuide/Download).

## Generating JSON Schema from example JSON

Go to https://jsonschema.net/ to generate a basic JSON Schema from the example JSON document.

## Enriching The Schema

This script enriches the basic JSON Schema generated using https://jsonschema.net/ with attribute information (datatype, format, string maxLength) gleaned from the MDM Attribute mappings spreadsheet.

The MDM attribute mapping tab should be exported as a CSV and is passed to the script using the ``--mapping`` parameter.

```bash
$ python3 enrich_schema.py --help
usage: enrich_schema.py [-h] [--mapping MAPPING] [--lov LOV] infile outfile

positional arguments:
  infile             base JSON schema
  outfile            enriched JSON schema

optional arguments:
  -h, --help         show this help message and exit
  --mapping MAPPING  MDM Attribute Mapping CSV
  --lov LOV          MDM LOV CSV

```

example:
```bash
$ python3 enrich_schema.py --mapping "MDM_Generic_Outbound_Attributes_V1.9.xlsx - Attribute Mapping.csv" mdm-product.schema.json mdm-product.v2.schema.json
```