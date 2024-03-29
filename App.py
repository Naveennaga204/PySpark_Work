from flask import Flask, render_template, request, redirect, url_for, flash
import pyspark
from pyspark.sql import SparkSession
import spark_df_profiling
import os
import re
spark = SparkSession.builder.appName("myapp").getOrCreate()

app = Flask(__name__)
func_rules = ["x"]

@app.route('/',methods=["GET", "POST"])
def Index():
    #Generates the funcational ruls
    lst1 =[]
    if request.method == 'POST':
        lst1 = to_html() 

    return render_template("index.html",rules=lst1)

    
#######################################################################################
 
#######################################################################################
def to_html():

    """
    Generate a HTML report from summary statistics and a given sample
    Parameters
    ----------
    sample: DataFrame containing the sample you want to print
    stats_object: Dictionary containing summary statistics. Should be generated with an appropriate describe() function
    Returns
    -------
    str, containing profile report in HTML format
    """

    df = spark.read.csv("C:/Users/home/Downloads/nasa-meteorite-landings/nasa-meteorite-landings/data/meteorite_landings.csv",header=True)
    report = spark_df_profiling.ProfileReport(df)
    report.to_file("C:/Users/home/OneDrive/Pictures/example.html")
    stats_object = report.description_set  #pandas dataframe with all columns and stats
    import sys
    try:
        from StringIO import BytesIO
    except ImportError:
        from io import BytesIO

    try:
        from urllib import quote
    except ImportError:
        from urllib.parse import quote

    import base64
    from itertools import combinations

    import matplotlib
    matplotlib.use('Agg')

    import numpy as np
    import json
    import pandas as pd
    import spark_df_profiling.formatters as formatters, spark_df_profiling.templates as templates
    from matplotlib import pyplot as plt
    from pkg_resources import resource_filename
    import six
    from pyspark.sql import DataFrame as SparkDataFrame
    from pyspark.sql.functions import (abs as df_abs, col, count, countDistinct,
                                       max as df_max, mean, min as df_min,
                                       sum as df_sum, when
                                       )

    # Backwards compatibility with Spark 1.5:
    try:
        from pyspark.sql.functions import variance, stddev, kurtosis, skewness
        spark_version = "1.6+"
    except ImportError:
        from pyspark.sql.functions import pow as df_pow, sqrt
        def variance_custom(column, mean, count):
            return df_sum(df_pow(column - mean, int(2))) / float(count-1)
        def skewness_custom(column, mean, count):
            return ((np.sqrt(count) * df_sum(df_pow(column - mean, int(3)))) / df_pow(sqrt(df_sum(df_pow(column - mean, int(2)))),3))
        def kurtosis_custom(column, mean, count):
            return ((count*df_sum(df_pow(column - mean, int(4)))) / df_pow(df_sum(df_pow(column - mean, int(2))),2)) -3
        spark_version = "<1.6" 
    n_obs = stats_object['table']['n']

    #
    sample = report.get_description()['variables']
    value_formatters = formatters.value_formatters
    row_formatters = formatters.row_formatters

    if not isinstance(sample, pd.DataFrame):
        raise TypeError("sample must be of type pandas.DataFrame")

    if not isinstance(stats_object, dict):
        raise TypeError("stats_object must be of type dict. Did you generate this using the spark_df_profiling.describe() function?")

    if set(stats_object.keys()) != {'table', 'variables', 'freq'}:
        raise TypeError("stats_object badly formatted. Did you generate this using the spark_df_profiling-eda.describe() function?")

    def fmt(value, name):
        if not isinstance(value, list):
               
                
            if pd.isnull(value):
                return ""
        else:
            if not value:
                return "[]"

        if name in value_formatters:
            return value_formatters[name](value)
        elif isinstance(value, float):
            return value_formatters[formatters.DEFAULT_FLOAT_FORMATTER](value)
        else:
            if sys.version_info.major == 3:
                return str(value)
            else:
                return unicode(value)

    def freq_table(freqtable, n, var_table, table_template, row_template, max_number_of_items_in_table):

        local_var_table = var_table.copy()
        freq_other_prefiltered = freqtable["***Other Values***"]
        freq_other_prefiltered_num = freqtable["***Other Values Distinct Count***"]
        freqtable = freqtable.drop(["***Other Values***", "***Other Values Distinct Count***"])

        freq_rows_html = u''

        freq_other = sum(freqtable[max_number_of_items_in_table:]) + freq_other_prefiltered
        freq_missing = var_table["n_missing"]
        max_freq = max(freqtable.values[0], freq_other, freq_missing)
        try:
            min_freq = freqtable.values[max_number_of_items_in_table]
        except IndexError:
            min_freq = 0

        # TODO: Correctly sort missing and other

        def format_row(freq, label, extra_class=''):
            width = int(freq / float(max_freq) * 99) + 1
            if width > 20:
                label_in_bar = freq
                label_after_bar = ""
            else:
                label_in_bar = "&nbsp;"
                label_after_bar = freq

            return row_template.render(label=label,
                                       width=width,
                                       count=freq,
                                       percentage='{:2.1f}'.format(freq / float(n) * 100),
                                       extra_class=extra_class,
                                       label_in_bar=label_in_bar,
                                       label_after_bar=label_after_bar)

        for label, freq in six.iteritems(freqtable[0:max_number_of_items_in_table]):
            freq_rows_html += format_row(freq, label)

        if freq_other > min_freq:
            freq_rows_html += format_row(freq_other,
                                         "Other values (%s)" % (freqtable.count()
                                                                + freq_other_prefiltered_num
                                                                - max_number_of_items_in_table),
                                         extra_class='other')

        if freq_missing > min_freq:
            freq_rows_html += format_row(freq_missing, "(Missing)", extra_class='missing')

        return table_template.render(rows=freq_rows_html, varid=hash(idx))

    # Variables
    rows_html = u""
    messages = []

    for idx, row in stats_object['variables'].iterrows():

        formatted_values = {'varname': idx, 'varid': hash(idx)}
        row_classes = {}

        for col, value in six.iteritems(row):
            formatted_values[col] = fmt(value, col)

        for col in set(row.index) & six.viewkeys(row_formatters):
            row_classes[col] = row_formatters[col](row[col])
            if row_classes[col] == "alert" and col in templates.messages:
                messages.append(templates.messages[col].format(formatted_values, varname = formatters.fmt_varname(idx)))

        if row['type'] == 'CAT':
            formatted_values['minifreqtable'] = freq_table(stats_object['freq'][idx], n_obs, stats_object['variables'].loc[idx],
                                                           templates.template('mini_freq_table'), templates.template('mini_freq_table_row'), 3)
            formatted_values['freqtable'] = freq_table(stats_object['freq'][idx], n_obs, stats_object['variables'].loc[idx],
                                                       templates.template('freq_table'), templates.template('freq_table_row'), 20)
            if row['distinct_count'] > 50:
                messages.append(templates.messages['HIGH_CARDINALITY'].format(formatted_values, varname = formatters.fmt_varname(idx)))
                row_classes['distinct_count'] = "alert"
            else:
                row_classes['distinct_count'] = ""

        if row['type'] == 'UNIQUE':
            obs = stats_object['freq'][idx].index

            formatted_values['firstn'] = pd.DataFrame(obs[0:3], columns=["First 3 values"]).to_html(classes="example_values", index=False)
            formatted_values['lastn'] = pd.DataFrame(obs[-3:], columns=["Last 3 values"]).to_html(classes="example_values", index=False)

            if n_obs > 40:
                formatted_values['firstn_expanded'] = pd.DataFrame(obs[0:20], index=range(1, 21)).to_html(classes="sample table table-hover", header=False)
                formatted_values['lastn_expanded'] = pd.DataFrame(obs[-20:], index=range(n_obs - 20 + 1, n_obs+1)).to_html(classes="sample table table-hover", header=False)
            else:
                formatted_values['firstn_expanded'] = pd.DataFrame(obs, index=range(1, n_obs+1)).to_html(classes="sample table table-hover", header=False)
                formatted_values['lastn_expanded'] = ''

        rows_html += templates.row_templates_dict[row['type']].render(values=formatted_values, row_classes=row_classes)

        if row['type'] in {'CORR', 'CONST'}:
            formatted_values['varname'] = formatters.fmt_varname(idx)
            messages.append(templates.messages[row['type']].format(formatted_values))


    # Overview
    formatted_values = {k: fmt(v, k) for k, v in six.iteritems(stats_object['table'])}

    row_classes={}
    for col in six.viewkeys(stats_object['table']) & six.viewkeys(row_formatters):
        row_classes[col] = row_formatters[col](stats_object['table'][col])
        if row_classes[col] == "alert" and col in templates.messages:
            messages.append(templates.messages[col].format(formatted_values, varname = formatters.fmt_varname(idx)))

    messages_html = u''
    for msg in messages:
        messages_html += templates.message_row.format(message=msg)
    lst = []
    for val in messages:
        x,y,z = re.findall(r'>(.*?)<', val)
        lst.append(x+y+z)
    
    # Column List in file
    col_list = []
    for x in report.get_description()['variables'].index:
        col_list.append(x)

    for col1 in col_list:
    # high cardinality test :should not be more than 90 %
    
        distinct_count = report.get_description()['variables'].loc[col1,'distinct_count']
        count = report.get_description()['variables'].loc[col1,'count']
        perc_cardinailty = (distinct_count/ count) * 100
        if perc_cardinailty > 90:
            lst.append(f"Column \"{col1}\" has {perc_cardinailty:.2f} cardinality. Please check the data type of this column if it is correct or not!")

    # Missing value : should not be more than 70 %
    
        perc_missing = report.get_description()['variables'].loc[col1,'p_missing']  * 100
    
        count_missing = report.get_description()['variables'].loc[col1,'p_missing']  * 100
    
        if perc_missing > 70:
            lst.append(f"Column \"{col1}\" has {count_missing} / {perc_missing:.2f}% values. Please apply imputation method i.e. filling these column values!")        

    return lst
#templates.template('base').render({'overview_html': overview_html, 'rows_html': rows_html, 'sample_html': sample_html})
#######################################################################################




if __name__ == "__main__":
    app.run(debug=True)