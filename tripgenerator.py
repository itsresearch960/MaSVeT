import tkinter as tk
from tkinter import Canvas
from PIL import Image, ImageTk, ImageDraw
import sumolib
import xml.etree.ElementTree as ET
import math
import logging
import os
import random
import numpy as np

# Load SUMO network
net = sumolib.net.readNet('new.net.xml')

# Parse for netOffset (not used but kept)
tree = ET.parse('new.net.xml')
root = tree.getroot()
location = root.find('location')
netOffset = tuple(map(float, location.attrib['netOffset'].split(',')))

# Logging setup
log_filepath = os.path.join(os.getcwd(), 'dictionary_log2.log')
logging.basicConfig(
    filename=log_filepath,
    filemode='w',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger()

def draw_network_image(net, width=800, height=600):
    xmin, ymin, xmax, ymax = net.getBoundary()
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)
    for edge in net.getEdges():
        shape = edge.getShape()
        pts = [
            (
                int((x - xmin)/(xmax-xmin)*width),
                int((y - ymin)/(ymax-ymin)*height)
            ) for x,y in shape
        ]
        draw.line(pts, fill="black", width=1)
    return img

class DrawBoundingBox:
    def __init__(self, root, net, netOffset):
        self.root = root
        self.net = net
        self.netOffset = netOffset
        self.stage = 0
        self.res_count = 0
        self.com_count = 0
        self.res_areas = {}
        self.com_areas = {}
        self.res_edge = {}
        self.com_edge = {}
        self.city_param = {}
        self.params_list = [
            "EV : Non-EV ratio (e.g. 4,6)",
            "Timeslot Size (in Hour)",
            "Number of days for simulation",
            "Population Density in Residential area",
            "Population Density in Commercial area",
            "Vehicle Ownership"
        ]
        # Canvas & image
        self.canvas = Canvas(root, width=800, height=600, bg="white")
        self.canvas.pack()
        self.img = draw_network_image(net)
        self.photo = ImageTk.PhotoImage(self.img)
        self.canvas.create_image(0,0,anchor="nw",image=self.photo)
        # drawing vars
        self.start_x = self.start_y = None
        self.rect = self.bbox = None
        # bind
        self.canvas.bind("<Button-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        # initial prompt
        self.prompt = tk.Label(root, text="Enter residential,commercial counts (e.g. 2,1):")
        self.prompt.pack()
        self.entry = tk.Entry(root); self.entry.pack()
        self.btn_enter = tk.Button(root, text="Enter", command=self.set_counts)
        self.btn_enter.pack()
        self.btn_submit = tk.Button(root, text="Submit", command=self.submit)
        self.btn_submit.pack_forget()

    def set_counts(self):
        r,c = map(int, self.entry.get().split(','))
        self.res_count, self.com_count = r,c
        self.prompt.pack_forget(); self.entry.pack_forget(); self.btn_enter.pack_forget()
        self.total = r+c
        self.next_area()

    def next_area(self):
        if self.stage < self.res_count:
            txt = f"Draw Residential Area {self.stage+1}"
        else:
            txt = f"Draw Commercial Area {self.stage-self.res_count+1}"
        self.prompt.config(text=txt); self.prompt.pack()

    def on_press(self, e):
        self.start_x, self.start_y = e.x,e.y
        self.rect = self.canvas.create_rectangle(e.x,e.y,e.x,e.y,outline='red')

    def on_drag(self, e):
        self.canvas.coords(self.rect,self.start_x,self.start_y,e.x,e.y)

    def on_release(self, e):
        self.bbox = (self.start_x,self.start_y,e.x,e.y)
        self.btn_submit.pack()

    def submit(self):
        if not self.bbox: return
        x1,y1,x2,y2 = self.bbox
        xmin,ymin,xmax,ymax = self.net.getBoundary()
        def to_sumo(x,y):
            return xmin + (x/800)*(xmax-xmin), ymin + (y/600)*(ymax-ymin)
        s1 = to_sumo(x1,y1); s2 = to_sumo(x2,y2)
        latlon = (*net.convertXY2LonLat(*s1),*net.convertXY2LonLat(*s2))
        if self.stage < self.res_count:
            self.res_areas[len(self.res_areas)+1]={"latlon":latlon}
        else:
            self.com_areas[len(self.com_areas)+1]={"latlon":latlon}
        self.stage+=1; self.btn_submit.pack_forget()
        if self.stage<self.total: self.next_area()
        else: self.done_areas()

    def done_areas(self):
        self.canvas.pack_forget(); self.prompt.pack_forget()
        self.ask_city_params()

    def ask_city_params(self):
        win = tk.Toplevel(self.root); win.title("City Parameters")
        self.param_entries={}
        for i,p in enumerate(self.params_list):
            r=i//2; c=(i%2)*2
            tk.Label(win,text=p).grid(row=r,column=c,sticky="e")
            e=tk.Entry(win,width=10); e.grid(row=r,column=c+1)
            self.param_entries[p]=e
        tk.Button(win,text="Submit",command=self.collect_city).grid(row=3,column=0,columnspan=4,pady=10)

    def collect_city(self):
        for p,e in self.param_entries.items(): self.city_param[p]=e.get()
        self.build_edge_lists()
        tsz=float(self.city_param[self.params_list[1]])
        T=int(24/tsz)
        self.ask_prc_pcr(T)

    def ask_prc_pcr(self,T):
        win=tk.Toplevel(self.root); win.title("PRC/PCR")
        self.prc_entries={}; self.pcr_entries={}
        for i in range(T):
            tk.Label(win,text=f"PRC {i+1}:").grid(row=i,column=0)
            pe=tk.Entry(win,width=10); pe.grid(row=i,column=1)
            tk.Label(win,text=f"PCR {i+1}:").grid(row=i,column=2)
            ce=tk.Entry(win,width=10); ce.grid(row=i,column=3)
            self.prc_entries[i]=pe; self.pcr_entries[i]=ce
        tk.Button(win,text="Submit",command=self.collect_prc).grid(row=T,column=0,columnspan=4)

    def collect_prc(self):
        PRC={i:tuple(map(float,e.get().split(',')))
             for i,e in self.prc_entries.items()}
        PCR={i:tuple(map(float,e.get().split(',')))
             for i,e in self.pcr_entries.items()}
        logger.info("PRC: %s",PRC)
        logger.info("PCR: %s",PCR)
        self.generate_trips(PRC,PCR)

    def build_edge_lists(self):
        self.res_edge={k:[] for k in self.res_areas}
        self.com_edge={k:[] for k in self.com_areas}
        for e in net.getEdges():
            s=net.convertXY2LonLat(*e.getFromNode().getCoord())
            t=net.convertXY2LonLat(*e.getToNode().getCoord())
            for k,v in self.res_areas.items():
                minx,miny,maxx,maxy=v["latlon"]
                if minx<=s[0]<=maxx and miny<=s[1]<=maxy and minx<=t[0]<=maxx and miny<=t[1]<=maxy:
                    self.res_edge[k].append(e.getID())
            for k,v in self.com_areas.items():
                minx,miny,maxx,maxy=v["latlon"]
                if minx<=s[0]<=maxx and miny<=s[1]<=maxy and minx<=t[0]<=maxx and miny<=t[1]<=maxy:
                    self.com_edge[k].append(e.getID())

    def calc_area(self):
        R=6371.0
        self.res_km={}; self.com_km={}
        for dct,out in ((self.res_areas,self.res_km),(self.com_areas,self.com_km)):
            for k,v in dct.items():
                minx,miny,maxx,maxy=v["latlon"]
                dlat=math.radians(maxy-miny); dlon=math.radians(maxx-minx)
                la1,la2=math.radians(miny),math.radians(maxy)
                a=math.sin(dlat/2)**2+math.cos(la1)*math.cos(la2)*math.sin(dlon/2)**2
                c=2*math.atan2(math.sqrt(a),math.sqrt(1-a))
                h=R*c; w=R*dlon*math.cos((la1+la2)/2)
                out[k]=h*w
                                # ─── ADD THESE LINES ─────────────────────────────────────────────
                if out is self.res_km:
                    logger.info("Residential region %d area: %.3f km²", k, out[k])
                else:
                    logger.info("Commercial region %d area: %.3f km²", k, out[k])
                # ────────────────────────────────────────────────────────────────

    def generate_trips(self, PRC, PCR):
        ent = self.city_param
        ev_ratio = list(map(int, ent[self.params_list[0]].split(',')))
        tsz = float(ent[self.params_list[1]])
        days = int(ent[self.params_list[2]])
        respd = float(ent[self.params_list[3]])
        compd = float(ent[self.params_list[4]])
        own = float(ent[self.params_list[5]])
        pal = int(tsz * 3600)
        T = int(24 / tsz)

        ev_types = ['ev_car', 'ev_truck', 'ev_bus']
        foss_types = ['foss_car', 'foss_truck', 'foss_bus']

        self.build_edge_lists()
        self.calc_area()
        total_res = sum(self.res_km.values())
        total_com = sum(self.com_km.values())

        rho = []
        RCN = {}
        RRN = {}
        CRN = {}
        CCN = {}

        for t in range(T):
            mu, sig = PRC[t]
            q = np.clip(np.random.normal(mu, sig), 0.0, 100.0) / 100
            if q <= 0 or math.isnan(q):
                q = mu / 100
            rt = q * total_res * respd * own
            rho.append(rt)
            RCN[t] = np.random.poisson(lam=rt, size=days)
            logger.info("Timeslot %d: rho=%s, RCN=%s", t, rt, RCN[t])

            lam_rr = (1 - q) * total_res * respd * own
            RRN[t] = np.random.poisson(lam=lam_rr, size=days)
            logger.info("Timeslot %d: rho_RR=%s, RRN=%s", t, lam_rr, RRN[t])

            mu2, sig2 = PCR[t]
            q2 = np.clip(np.random.normal(mu2, sig2), 0.0, 100.0) / 100
            if q2 <= 0 or math.isnan(q2):
                q2 = mu2 / 100
            lam_cr = q2 * total_com * compd * own
            CRN[t] = np.random.poisson(lam=lam_cr, size=days)
            logger.info("Timeslot %d: rho_CR=%s, CRN=%s", t, lam_cr, CRN[t])

            lam_cc = (1 - q2) * total_com * compd * own
            CCN[t] = np.random.poisson(lam=lam_cc, size=days)
            logger.info("Timeslot %d: rho_CC=%s, CCN=%s", t, lam_cc, CCN[t])

        HUG = []
        trip_counts = {}  # NEW — Track region-to-region trip counts

        # Residential → Commercial
        for r, ra in self.res_km.items():
            pr = ra / total_res
            for c, ca in self.com_km.items():
                pc = ca / total_com
                for d in range(days):
                    for s in range(T):
                        n = int(pr * RCN[s][d] * pc)
                        for _ in range(n):
                            grp = random.choices(['EV', 'FOSS'], weights=ev_ratio, k=1)[0]
                            tt = random.choice(ev_types if grp == 'EV' else foss_types)
                            src = random.choice(self.res_edge[r])
                            dst = random.choice(self.com_edge[c])
                            dep = d * T * pal + s * pal + random.random() * pal
                            HUG.append([f"R{r}C{c}D{d}S{s}_{len(HUG)}", tt, dep, src, dst])
                            key = (f"R{r}", f"C{c}")  # NEW
                            trip_counts[key] = trip_counts.get(key, 0) + 1  # NEW

        # Residential → Residential
        for r, ra in self.res_km.items():
            pr = ra / total_res
            for rr, rra in self.res_km.items():
                prr = rra / total_res
                for d in range(days):
                    for s in range(T):
                        n = int(pr * RRN[s][d] * prr)
                        for _ in range(n):
                            grp = random.choices(['EV', 'FOSS'], weights=ev_ratio, k=1)[0]
                            tt = random.choice(ev_types if grp == 'EV' else foss_types)
                            src = random.choice(self.res_edge[r])
                            dst = random.choice(self.res_edge[rr])
                            dep = d * T * pal + s * pal + random.random() * pal
                            HUG.append([f"R{r}R{rr}D{d}S{s}_{len(HUG)}", tt, dep, src, dst])
                            key = (f"R{r}", f"R{rr}")  # NEW
                            trip_counts[key] = trip_counts.get(key, 0) + 1  # NEW

        # Commercial → Residential
        for c, ca in self.com_km.items():
            pc = ca / total_com
            for r, ra in self.res_km.items():
                pr = ra / total_res
                for d in range(days):
                    for s in range(T):
                        n = int(pc * CRN[s][d] * pr)
                        for _ in range(n):
                            grp = random.choices(['EV', 'FOSS'], weights=ev_ratio, k=1)[0]
                            tt = random.choice(ev_types if grp == 'EV' else foss_types)
                            src = random.choice(self.com_edge[c])
                            dst = random.choice(self.res_edge[r])
                            dep = d * T * pal + s * pal + random.random() * pal
                            HUG.append([f"C{c}R{r}D{d}S{s}_{len(HUG)}", tt, dep, src, dst])
                            key = (f"C{c}", f"R{r}")  # NEW
                            trip_counts[key] = trip_counts.get(key, 0) + 1  # NEW

        # Commercial → Commercial
        for c, ca in self.com_km.items():
            pc = ca / total_com
            for cc, cca in self.com_km.items():
                pcc = cca / total_com
                for d in range(days):
                    for s in range(T):
                        n = int(pc * CCN[s][d] * pcc)
                        for _ in range(n):
                            grp = random.choices(['EV', 'FOSS'], weights=ev_ratio, k=1)[0]
                            tt = random.choice(ev_types if grp == 'EV' else foss_types)
                            src = random.choice(self.com_edge[c])
                            dst = random.choice(self.com_edge[cc])
                            dep = d * T * pal + s * pal + random.random() * pal
                            HUG.append([f"C{c}C{cc}D{d}S{s}_{len(HUG)}", tt, dep, src, dst])
                            key = (f"C{c}", f"C{cc}")  # NEW
                            trip_counts[key] = trip_counts.get(key, 0) + 1  # NEW

        # Print the trip count summary
        print("\nTrip Count Between Region Pairs:")
        for k, v in sorted(trip_counts.items()):
            print(f"{k[0]} → {k[1]} : {v} trips")

        # Continue with your existing XML writing logic (unchanged)
        ...

        with open('sim_dip.odtrips.xml','w') as f:
            f.write('<routes>\n')
            # EV types with full params:
            f.write('<vType id="ev_car"   vClass="passenger" mass="1500" loading="0" length="4.5"  maxSpeed="80.0" accel="3.0" decel="4.5" sigma="0.5" tau="1.0" emissionClass="Energy/unknown">\n')
            f.write('  <param key="has.battery.device" value="true" />\n')
            f.write('  <param key="device.battery.capacity" value="20000" />\n')
            f.write('  <param key="maximumPower" value="1000" />\n')
            f.write('  <param key="device.battery.maximumChargeRate" value="150000" />\n')
            f.write('  <param key="frontSurfaceArea" value="5" />\n')
            f.write('  <param key="airDragCoefficient" value="0.6" />\n')
            f.write('  <param key="rotatingMass" value="100" />\n')
            f.write('  <param key="radialDragCoefficient" value="0.5" />\n')
            f.write('  <param key="rollDragCoefficient" value="0.01" />\n')
            f.write('  <param key="constantPowerIntake" value="100" />\n')
            f.write('  <param key="propulsionEfficiency" value="0.9" />\n')
            f.write('  <param key="recuperationEfficiency" value="0.0" />\n')
            f.write('  <param key="stoppingThreshold" value="0.1" />\n')
            f.write('  <param key="device.battery.chargeLevelTable" value="0 0.5 1" />\n')
            f.write('  <param key="device.battery.chargeCurveTable" value="150000 75000 30000" />\n')
            f.write('</vType>\n')
            f.write('<vType id="ev_truck" vClass="truck"     mass="12000" loading="0" length="12.0" maxSpeed="60.0" accel="1.2" decel="3.0" sigma="0.5" tau="1.0" emissionClass="Energy/unknown">\n')
            f.write('  <param key="has.battery.device" value="true" />\n')
            f.write('  <param key="device.battery.capacity" value="30000" />\n')
            f.write('  <param key="maximumPower" value="1500" />\n')
            f.write('  <param key="device.battery.maximumChargeRate" value="200000" />\n')
            f.write('  <param key="frontSurfaceArea" value="8" />\n')
            f.write('  <param key="airDragCoefficient" value="0.7" />\n')
            f.write('  <param key="rotatingMass" value="300" />\n')
            f.write('  <param key="radialDragCoefficient" value="0.6" />\n')
            f.write('  <param key="rollDragCoefficient" value="0.02" />\n')
            f.write('  <param key="constantPowerIntake" value="200" />\n')
            f.write('  <param key="propulsionEfficiency" value="0.85" />\n')
            f.write('  <param key="recuperationEfficiency" value="0.1" />\n')
            f.write('  <param key="stoppingThreshold" value="0.1" />\n')
            f.write('  <param key="device.battery.chargeLevelTable" value="0 0.5 1" />\n')
            f.write('  <param key="device.battery.chargeCurveTable" value="150000 80000 35000" />\n')
            f.write('</vType>\n')
            f.write('<vType id="ev_bus"   vClass="bus"       mass="8000"  loading="0" length="13.0" maxSpeed="50.0" accel="1.5" decel="3.5" sigma="0.5" tau="1.0" emissionClass="Energy/unknown">\n')
            f.write('  <param key="has.battery.device" value="true" />\n')
            f.write('  <param key="device.battery.capacity" value="25000" />\n')
            f.write('  <param key="maximumPower" value="1200" />\n')
            f.write('  <param key="device.battery.maximumChargeRate" value="180000" />\n')
            f.write('  <param key="frontSurfaceArea" value="10" />\n')
            f.write('  <param key="airDragCoefficient" value="0.8" />\n')
            f.write('  <param key="rotatingMass" value="400" />\n')
            f.write('  <param key="radialDragCoefficient" value="0.7" />\n')
            f.write('  <param key="rollDragCoefficient" value="0.015" />\n')
            f.write('  <param key="constantPowerIntake" value="250" />\n')
            f.write('  <param key="propulsionEfficiency" value="0.8" />\n')
            f.write('  <param key="recuperationEfficiency" value="0.2" />\n')
            f.write('  <param key="stoppingThreshold" value="0.1" />\n')
            f.write('  <param key="device.battery.chargeLevelTable" value="0 0.5 1" />\n')
            f.write('  <param key="device.battery.chargeCurveTable" value="150000 90000 40000" />\n')
            f.write('</vType>\n')
            # fossil types
            for vt in [
                '<vType id="foss_car"   vClass="passenger" length="4.5"  maxSpeed="70.0" accel="3.0" decel="4.5" sigma="0.0" />',
                '<vType id="foss_truck" vClass="truck"     length="12.0" maxSpeed="60.0" accel="1.5" decel="3.5" sigma="0.0" />',
                '<vType id="foss_bus"   vClass="bus"       length="13.0" maxSpeed="50.0" accel="2.0" decel="4.0" sigma="0.0" />'
            ]:
                f.write(vt + "\n")
            # trip entries
            for trip in sorted(HUG, key=lambda x: x[2]):
                f.write(
                    f'<trip id="{trip[0]}" type="{trip[1]}" '
                    f'depart="{trip[2]:.2f}" from="{trip[3]}" to="{trip[4]}" />\n'
                )
            f.write('</routes>\n')
        print("Trip File Generation Successful: sim_dip.odtrips.xml")
        self.root.destroy()

if __name__=="__main__":
    root=tk.Tk()
    DrawBoundingBox(root, net, netOffset)
    root.mainloop()
