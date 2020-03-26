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
import parse
import pathlib
import sys
from functools import partial
from collections import defaultdict


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

def analyze(message, cumulative=False):
    lines = message.split("\n")
    date = None
    data = dict()
    if cumulative:
        cumulative_totals = {}

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
            if cumulative:
                if date not in cumulative_totals:
                    cumulative_totals[date] = defaultdict(list)
                cumulative_totals[date]["views"].append(result["views"])
                cumulative_totals[date]["users"].append(result["users"])
                cumulative_totals[date]["view_time"].append(result["time"])

    srcs = []
    titles = []
    for slug, value in data.items():
        dates = np.array(value['date'], dtype=np.datetime64)
        views = np.array(value['views'])
        if cumulative:
            srcs.append(ColumnDataSource(data=dict(date=dates, info=np.cumsum(views))))
            titles.append(slug + " Cumulative")
        else:
            srcs.append(ColumnDataSource(data=dict(date=dates, info=views)))
            titles.append(slug)

    if cumulative:
        srcs.append(ColumnDataSource(data=dict(
            date=np.array(list(cumulative_totals.keys()), dtype=np.datetime64),
            info=np.cumsum([sum(v["views"]) for v in cumulative_totals.values()]),
        )))
        titles.append("Total Cumulative Views")

    return srcs, titles


def graph_it(args, doc):
    path = pathlib.Path(args.input_file)
    cumulative = args.cumulative
    srcs, titles = analyze(path.read_text(), cumulative)

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
    parser.add_argument("-c", "--cumulative", action="store_true", help="Plot cumulative values")
    parser.add_argument("input_file", help="raw text copied from slack")
    return parser.parse_args()


def start_server(args, address, port, url, attempts=100):
    g = partial(graph_it, args)
    while attempts:
        attempts -= 1
        try:
            server = Server(
                {url: g},
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
        server, port = start_server(args, address, port, url)
    except Exception as ex:
        print("Failed:", ex)
        sys.exit()

    try:
        print(f"Opening Bokeh application on http://{address}:{port}{url}")
        server.io_loop.add_callback(server.show, url)
        server.io_loop.start()
    except KeyboardInterrupt:
        print("\nShutting Down")
