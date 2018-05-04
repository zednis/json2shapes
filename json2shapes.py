import json
import re
import argparse
import pandas


def convert(name):
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).upper()


def ontology_sheet():

    columns = ['Ontology Name', 'Comment', 'Namespace URI', 'Prefix']

    data = [
        {'Ontology Name': 'XML Schema',
         'Comment': 'The XML Schema vocabulary which provides terms for simple data types.',
         'Namespace URI': 'http://www.w3.org/2001/XMLSchema#',
         'Prefix': 'xsd'},
        {'Ontology Name': 'Konig Core Ontology',
         'Comment': 'A vocabulary for enriched semantic models that enable ontology-based engineering solutions.',
         'Namespace URI': 'http://www.konig.io/ns/core/',
         'Prefix': 'konig'},
        {'Ontology Name': 'Pearson Data Shapes',
         'Comment': 'The ontology for data shapes defined by Pearson',
         'Namespace URI': 'https://schema.pearson.com/shapes/',
         'Prefix': 'shape'},
        {'Ontology Name': 'Alias Namespace',
         'Comment': 'A namespace that contains alternative names for properties.',
         'Namespace URI': 'http://example.com/ns/alias/',
         'Prefix': 'alias'},
        {'Ontology Name': 'SHACL Vocabulary',
         'Comment': 'W3C Shapes Constraint Language (SHACL)',
         'Namespace URI': 'http://www.w3.org/ns/shacl#',
         'Prefix': 'sh'
        }
    ]

    df = pandas.DataFrame().from_dict(data)
    return columns, df


def shapes_sheet(data):
    columns = ['Shape Id', 'Comment', 'Scope Class', 'Datasource', 'Shape Type', 'One Of', 'IRI Template']

    shapes = []
    shape_set = set()

    for row in data:
        shape = row["Shape Id"]
        if shape not in shape_set:
            shape_set.add(shape)
            shapes.append({'Shape Id': shape})

    df = pandas.DataFrame().from_dict(shapes)
    return columns, df


def process(df, name, node, primary_key=None, ref_node=None, parent_node=None, prefix=None):

    if "properties" in node:

        properties = node["properties"]

        name_uri = "shape:{}_{}".format(convert(prefix), convert(name)) if prefix else "shape:{}".format(convert(name))

        # synthetic key
        if not parent_node:
            df.append({'Shape Id': name_uri,
                       'Property Id': 'alias:STAGE_ID',
                       'Value Type': 'xsd:string',
                       'Stereotype': 'konig:syntheticKey',
                       'Min Count': 1,
                       'Max Count': 1
                       })

        if ref_node:

            df.append({'Shape Id': name_uri,
                       'Property Id': "alias:"+convert(ref_node)+"_FK",
                       'Value Type': 'xsd:string',
                       'Stereotype': 'konig:foreignKey',
                       'Min Count': 1,
                       'Max Count': 1
                       })

        for k, v in properties.items():

            if "type" in v and (v["type"] == "object" or "object" in v["type"]):
                prop = "{}_{}".format(parent_node, convert(k)) if parent_node else "{}".format(convert(k))
                process(df, name, v, parent_node=prop, prefix=prefix)

            elif "type" in v and (v["type"] == "array" or "array" in v["type"]):
                process(df, convert(k), v["items"], ref_node=name, prefix=prefix)

            else:
                prop = "alias:{}_{}".format(parent_node, convert(k)) if parent_node else "alias:{}".format(convert(k))
                row = {'Shape Id': name_uri, 'Property Id': prop}

                # determine 'Value Type'
                if "type" in v and (v["type"] == "string" or "string" in v["type"]):

                    # TODO we should add a format for integer vs decimal
                    if "format" in v and (v["format"] == "number" or "number" in v["format"]):
                        row.update({'Value Type': "xsd:decimal"})
                    elif "format" in v and (v["format"] == "date-time" or "date-time" in v["format"]):
                        row.update({'Value Type': "xsd:datetime"})
                    else:
                        row.update({'Value Type': 'xsd:string'})
                else:
                    row.update({'Value Type': 'xsd:string'})

                if "maxLength" in v and v["maxLength"] and v["maxLength"] != "N/A":
                    row.update({'Max Length': int(v["maxLength"])})

                if "type" in v and "null" in v["type"]:
                    row.update({'Min Count': 0})
                else:
                    row.update({'Min Count': 1})

                row.update({'Max Count': 1})

                if k == primary_key:
                    row.update({'Stereotype': 'konig:primaryKey', 'Min Count': 1})

                df.append(row)


def run(args):

    df = []

    with open(args.schema) as json_schema:
        schema = json.load(json_schema)
        process(df, args.base, schema, primary_key=args.primary_key, prefix=args.prefix)

    writer = pandas.ExcelWriter(args.workbook)

    ontology_columns, ontology_df = ontology_sheet()
    ontology_df.to_excel(writer, 'Ontologies', columns=ontology_columns, index=False)

    shapes_columns, shapes_df = shapes_sheet(df)
    shapes_df.to_excel(writer, 'Shapes', columns=shapes_columns, index=False)

    columns = ['Shape Id', 'Property Id', 'Value Type', 'Stereotype', 'Min Count', 'Max Count', 'Max Length']
    _df = pandas.DataFrame().from_dict(df)
    _df.to_excel(writer, 'Property Constraints', columns=columns, index=False)

    writer.save()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument('--base', default="Product")
    parser.add_argument('--primary-key', default="ppid")
    parser.add_argument('--prefix')
    parser.add_argument('schema', help='base JSON schema')
    parser.add_argument('workbook', help='workbook with data shapes')

    args = parser.parse_args()
    run(args)
