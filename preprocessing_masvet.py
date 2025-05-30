#!/usr/bin/env python
from __future__ import absolute_import
from __future__ import print_function
import gzip
import ssl
import json
import collections
import sumolib
import os
import subprocess
import tkinter as tk
try:
    import httplib
    import urlparse
    from urllib2 import urlopen
except ImportError:
    import http.client as httplib
    import urllib.parse as urlparse
    from urllib.request import urlopen
try:
    THIS_DIR = os.path.abspath(os.path.dirname(__file__))
except NameError:
    THIS_DIR = os.getcwd()

TYPEMAP_DIR = os.path.join(THIS_DIR, "..", "data", "typemap")

# --- GUI to get bounding box ---
def get_bbox():
    try:
        global west, south, east, north
        west = float(entry_w.get())
        south = float(entry_s.get())
        east = float(entry_e.get())
        north = float(entry_n.get())
        print(f"Selected BBox: W={west}, S={south}, E={east}, N={north}")
        root.destroy()
    except Exception as e:
        print("Invalid input. Please enter valid float values.")

root = tk.Tk()
root.title("Enter OSM Bounding Box Coordinates")

tk.Label(root, text="West Longitude").grid(row=0, column=0)
tk.Label(root, text="South Latitude").grid(row=1, column=0)
tk.Label(root, text="East Longitude").grid(row=2, column=0)
tk.Label(root, text="North Latitude").grid(row=3, column=0)

entry_w = tk.Entry(root); entry_s = tk.Entry(root)
entry_e = tk.Entry(root); entry_n = tk.Entry(root)

entry_w.insert(0, "4.75")
entry_s.insert(0, "52.30")
entry_e.insert(0, "4.85")
entry_n.insert(0, "52.40")

entry_w.grid(row=0, column=1)
entry_s.grid(row=1, column=1)
entry_e.grid(row=2, column=1)
entry_n.grid(row=3, column=1)

tk.Button(root, text="Download and Convert", command=get_bbox).grid(row=4, columnspan=2, pady=10)
root.mainloop()


def readCompressed(conn, urlpath, query, filename):
    queryStringNode = []
    unionQueryString = """
    <union>
       %s
       <recurse type="node-relation" into="rels"/>
       <recurse type="node-way"/>
       <recurse type="way-relation"/>
     </union>
     <union>
        <item/>
        <recurse type="way-node"/>
     </union>""" % query

    finalQuery = """
    <osm-script timeout="240" element-limit="1073741824">
       %s
    <print mode="body"/>
    </osm-script>""" % unionQueryString

    conn.request("POST", "/" + urlpath, finalQuery, headers={'Accept-Encoding': 'gzip'})

    response = conn.getresponse()
    print(response.status, response.reason)
    if response.status == 200:
        with open(filename, "wb") as out:
            if response.getheader('Content-Encoding') == 'gzip':
                lines = gzip.decompress(response.read())
            else:
                lines = response.read()
            declClose = lines.find(b'>') + 1
            lines = (lines[:declClose]
                     + b"\n"
                     + sumolib.xml.buildHeader().encode()
                     + lines[declClose:])
            if filename.endswith(".gz"):
                out.write(gzip.compress(lines))
            else:
                out.write(lines)

def get():
    url = urlparse.urlparse("https://www.overpass-api.de/api/interpreter")
    if url.scheme == "https":
        conn = httplib.HTTPSConnection(url.hostname, url.port)
    else:
        conn = httplib.HTTPConnection(url.hostname, url.port)

    suffix = ".osm.xml.gz"
    filename = "osm_bbox" + suffix

    readCompressed(conn, url.path, '<bbox-query n="%s" s="%s" w="%s" e="%s"/>' %
                   (north, south, west, east), filename)
    conn.close()

if __name__ == "__main__":
    try:
        get()
    except ssl.CertificateError:
        print("Error with SSL certificate, try 'pip install -U certifi'.", file=sys.stderr)

# unzip and convert
command = ["gunzip", "-f", "osm_bbox.osm.xml.gz"]
subprocess.run(command, capture_output=True, text=True)

osm_file = "osm_bbox.osm.xml"
net_file = "city.net.xml"

subprocess.run([
    "netconvert",
    "--osm-files", osm_file,
    "--output-file", net_file
], check=True)

print("Network conversion successful: city.net.xml generated.")

command = [
    "osmfilter", "osm_bbox.osm.xml",     
    "--keep=amenity=charging_station"
]

with open("ev_stations.osm.xml", "w") as output_file:
    subprocess.run(command, stdout=output_file, text=True, check=True)

print("Filtering completed: ev_stations.osm.xml created.")

import xml.etree.ElementTree as ET
import sumolib
import logging
from pyproj import Transformer
import xml.dom.minidom

logging.basicConfig(
    filename='charging_station_extraction.log',
    filemode='w',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger()

net = sumolib.net.readNet('city.net.xml')
tree = ET.parse('city.net.xml')
root = tree.getroot()
location = root.find('location')
proj_params = location.attrib['projParameter']
netOffset = tuple(map(float, location.attrib['netOffset'].split(',')))

transformer = Transformer.from_crs("epsg:4326", proj_params, always_xy=True)

charging_stations = {}
try:
    osm_tree = ET.parse('ev_stations.osm.xml')
    osm_root = osm_tree.getroot()
except Exception as e:
    logger.error(f"Failed to load OSM file: {e}")
    raise

cs_id = 1
for node in osm_root.findall('node'):
    for tag in node.findall('tag'):
        if tag.attrib.get('k') == 'amenity' and tag.attrib.get('v') == 'charging_station':
            try:
                lat = float(node.attrib['lat'])
                lon = float(node.attrib['lon'])
                utm_x, utm_y = transformer.transform(lon, lat)
                x = utm_x + netOffset[0]
                y = utm_y + netOffset[1]
                charging_stations[f"cs_{cs_id}"] = (x, y)
                cs_id += 1
            except Exception as ex:
                logger.warning(f"Skipping node due to conversion error: {ex}")
                continue

logger.info(f"Extracted {len(charging_stations)} charging stations.")
root_elem = ET.Element("nodes")
for cs_id, (x, y) in charging_stations.items():
    node_elem = ET.SubElement(root_elem, "node", id=cs_id, x=str(x), y=str(y))
xml_str = ET.tostring(root_elem, encoding="utf-8")
pretty_xml = xml.dom.minidom.parseString(xml_str).toprettyxml(indent="  ")
with open("charging_stations_xy.xml", "w") as f:
    f.write(pretty_xml)
print("Charging stations saved to 'charging_stations_xy.xml'")
