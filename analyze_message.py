#!/usr/bin/env python3
"""Analyze Raw text from real python team slack and produce a graph. """

import argparse
from bokeh.layouts import row
from bokeh.models import ColumnDataSource
from bokeh.models.tools import HoverTool
from bokeh.models.widgets import CheckboxGroup
from bokeh.plotting import figure, curdoc
from bokeh.server.server import Server
from dateutil.parser import parse as date_parse
import numpy as np
import pandas as pd
import parse
import pathlib
import sys


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
        ('date', '@date{%F-%T}'),
        ('readers', '@info'),
    ]
    hover.formatters = {
        'date'      : 'datetime', # use 'datetime' formatter for 'date' field
    }
    # hover.mode = "vline"
    p.add_tools(hover)
    return p


def callback(selections):
    new_src = []
    new_titles = []
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

    srcs = []
    for value in data.values():
        dates = np.array(value['date'], dtype=np.datetime64)
        views = np.array(value['views'])
        srcs.append(ColumnDataSource(data=dict(date=dates, info=views)))

    return srcs, list(data.keys())


def graph_it(doc):
    path = pathlib.Path(sys.argv[1])
    srcs, titles = analyze(path.read_text())

    callback.srcs = srcs
    callback.titles = titles

    p = create_figure(titles, srcs)
    # doc.add_root(p)

    actives = [x for x in range(len(srcs))]
    callback.checkbox_group = CheckboxGroup(labels=titles, active=actives)
    callback.checkbox_group.on_click(callback)
    doc.add_root(row(callback.checkbox_group, p))

def get_command_line_args():
    """ Read command line args, of course."""
    parser = argparse.ArgumentParser()
    parser.add_argument("-n", "--no-checkbox", action="store_true")
    parser.add_argument("input_file", help="raw text copied from slack")
    return parser.parse_args()


def start_server(address, port, url, attempts=100):
    while attempts:
        attempts -= 1
        try:
            server = Server(
                {url: graph_it},
                num_procs=1,
                port=port,
                address=address,
                allow_websocket_origin=[f"{address}:{port}",],
            )
            server.start()
            return server, port
        except OSError as ex:
            if "Address already in use" in str(ex):
                print(f"Port {port} busy")
                port += 1
            else:
                raise ex
    raise Exception("Failed to find available port")


if __name__ == "__main__":
    args = get_command_line_args()
    # These can be added as command line args if you want to move them around
    port = 5006
    address = "localhost"
    url = "/"

    try:
        server, port = start_server(address, port, url)
    except Exception as ex:
        print("Failed:", ex)
        sys.exit()

    try:
        print(f"Opening Bokeh application on http://{address}:{port}{url}")
        server.io_loop.add_callback(server.show, url)
        server.io_loop.start()
    except KeyboardInterrupt:
        print("\nShutting Down")
