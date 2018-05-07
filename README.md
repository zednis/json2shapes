# json2shapes

## Dependencies

Running these scripts requires python3+.  For information on installing Python, visit the [Python Beginners Guide](https://wiki.python.org/moin/BeginnersGuide/Download).

The json2shape script depends on the the [pandas](https://pypi.org/project/pandas/) library for writing the workkbook to an excel file.

Pandas can be installed with the following command
```bash
$ pip3 install -U pandas
```

## Generating JSON Schema from example JSON

Go to https://jsonschema.net/ to generate a basic JSON Schema from the example JSON document.

## Enriching The Schema

This script enriches the basic JSON Schema generated using https://jsonschema.net/ with attribute information (datatype, format, string maxLength) gleaned from the MDM Attribute mappings spreadsheet.

The MDM attribute mapping tab should be exported as a CSV and is passed to the script using the ``--mapping`` parameter.

usage:
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

## Generating Workbook from JSON Schema

This script generates a konig workbook spreadsheet based on an input JSON Schema.

usage:
```bash
$ python3 json2shapes.py --help
usage: json2shapes.py [-h] [--config CONFIG] schema workbook

positional arguments:
  schema           base JSON schema
  workbook         workbook with data shapes

optional arguments:
  -h, --help       show this help message and exit
  --config CONFIG  path to INI config file

```

example:
```bash
$ python3 json2shapes.py --config=mdm-product.ini mdm-product.schema.json mdm-product-workbook.xlsx
```

## TODO
- add controlled vocabularies (< 20 items) to JSON Schema during enrich_schema.py