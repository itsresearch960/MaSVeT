import subprocess
lines1 = [
    "<configuration>",
    "<input>",
    "<net-file value=\"new.net.xml\"/>"
]

lines3 = [
    "</input>",
    "<output>"
]

lines5 = [
    "</output>",
    "<report>",
    "<xml-validation value=\"never\"/>",
    "<no-step-log value=\"true\"/>",
    "</report>",
    "</configuration>"
]


with open('duarcfg_file.trips2routes.duarcfg', 'w') as wfile:
    for l in lines1:
        wfile.write(l + '\n')
    wfile.write('<route-files value=\"'+'sim_dip.odtrips.xml"/>\n')
    for l in lines3:
        wfile.write(l + '\n')
    wfile.write('<output-file value=\"' + 'sim_dip.odtrips.rou.xml"/>\n')
    for l in lines5:
        wfile.write(l + '\n')
wfile.close()
command = "duarouter -c duarcfg_file.trips2routes.duarcfg --ignore-errors"
subprocess.run(command, shell=True)
        
        
            
