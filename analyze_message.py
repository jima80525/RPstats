#!/usr/bin/env python3.7
"""Analyze a message, store to csv"""

import pathlib
import sys

from bokeh.layouts import row
from bokeh.models import ColumnDataSource
from bokeh.models.tools import HoverTool
from bokeh.models.widgets import CheckboxGroup
from bokeh.plotting import figure, curdoc
from dateutil.parser import parse as date_parse
import numpy as np
import pandas as pd
import parse

PATTERNS = dict(
    date=parse.compile("Between {_} and {date}, your articles"),
    data=parse.compile(
        "→ realpython.com/{slug}/: {views:n} views, {users:n} users, {time} avg reading time"
    ),
)

colors = [
    "darkmagenta",
    "deeppink",
    "blue",
    "lime",
    "teal",
    "yellow",
    "turquoise",
    "lightcoral",
    "cyan",
    "black",
    "crimson",
    "green",
    "orangered",
    "red",
    "mediumvioletred",
    "lightsalmon",
]



def create_figure(titles, sources):
    p = figure(plot_height=800, plot_width=1200, title="articles",
               x_axis_type="datetime", x_axis_location="below",
               background_fill_color="#efefef", toolbar_location="above")
    p.yaxis.axis_label = 'views'
    for index, source in enumerate(sources):
        p.line('date', 'info', source=source, legend_label=titles[index],
               line_width=2, line_color=colors[index%len(colors)])
    p.legend.location = "top_left"
    p.legend.click_policy = "hide"


    hover = HoverTool()
    hover.tooltips=[
        ('time', '@date{%F-%T}'),
        ('rss', '@info'),
    ]
    hover.formatters = {
        'date'      : 'datetime', # use 'datetime' formatter for 'date' field
    }
    hover.mode = "vline"
    p.add_tools(hover)
    return p


TITLES = []
ORIG_LINES = []
SRCS = []

def callback(selections):
    print("JIMA CALLBACK")
    print("JIMA SRCS", callback.srcs)
    new_src = []
    new_titles = []
    # LINES.clear()
    for item in selections:
        new_src.append(callback.srcs[item])
        new_titles.append(callback.titles[item])
    p = create_figure(new_titles, new_src)
    curdoc().clear()
    curdoc().add_root(row(callback.checkbox_group, p))

def analyze(message):
    lines = message.split("\n")
    orig_lines = lines
    date = None
    data = dict()

    for line in lines:
        date_search = PATTERNS["date"].search(line)
        if date_search:
            date = date_parse(date_search.named["date"])

        data_search = PATTERNS["data"].search(line)
        if data_search:
            result = data_search.named
            mins, _, secs = result.pop("time").partition(":")
            result["time"] = int(secs) + int(mins) * 60
            if date:
                result["date"] = date
            slug = result["slug"]
            if slug not in data:
                data[slug] = {
                    "date":[],
                    "views":[],
                    "users":[],
                    "view_time":[],
                }
            data[slug]["date"].append(date)
            data[slug]["views"].append(result["views"])
            data[slug]["users"].append(result["users"])
            data[slug]["view_time"].append(result["time"])

    return data


def old_analyze(message):
    lines = message.split("\n")
    date = None
    data = list()

    for line in lines:
        date_search = PATTERNS["date"].search(line)
        if date_search:
            date = date_parse(date_search.named["date"])

        data_search = PATTERNS["data"].search(line)
        if data_search:
            result = data_search.named
            mins, _, secs = result.pop("time").partition(":")
            result["time"] = int(secs) + int(mins) * 60
            if date:
                result["date"] = date
            if "github-intro" in result["slug"]:
                data.append(result)

    return data

def main():
    path = pathlib.Path(sys.argv[1])
    print(f"Working on {path}")
    data = analyze(path.read_text())

    srcs = []
    for item, value in data.items():
        # print(item, value)
        dates = np.array(value['date'], dtype=np.datetime64)
        views = np.array(value['views'])
        srcs.append(ColumnDataSource(data=dict(date=dates, info=views)))


    callback.srcs = srcs
    titles = list(data.keys())
    callback.titles = titles
    p = create_figure(titles, srcs)
    # curdoc().add_root(p)

    actives = [x for x in range(len(srcs))]
    callback.checkbox_group = CheckboxGroup(labels=titles, active=actives)
    callback.checkbox_group.on_click(callback)
    curdoc().add_root(row(callback.checkbox_group, p))

    # curdoc().clear()
    # curdoc().add_root(row(checkbox_group, p))


    # output_path = path.with_suffix(".csv")
    # print(f"Writing output to {output_path}")
    # pd.DataFrame.from_dict(data).to_csv(output_path)



main()

