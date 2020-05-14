# RandomActivityGen

This tool provides an easy way to generate pseudo-realistic traffic scenarios for [SUMO](http://sumo.sourceforge.net/) by generating a population statistics file (`.stats.xml`) for the SUMO-tool; [ACTIVITYGEN](https://sumo.dlr.de/docs/ACTIVITYGEN.html).

RandomActivityGen works best for single city networks, and works even better with a random [NETGENERATE](https://sumo.dlr.de/docs/NETGENERATE.html) network. More continuous, circular cities render better results as the tool does not adjust for geographic features such as waterfronts, mountains, and parks.

## Setup

The project uses Python 3.
Dependencies can be installed by running:

```
pip install -r requirements.txt
```

Additional dependencies for running some scripts from the `testing` directory can be installed by running:

```
pip install -r testing/requirements.txt
```

The use of a virtual environment is recommended.

## Usage

**Required input:**

* A network file (`.net.xml`) as generated via [NETCONVERT](https://sumo.dlr.de/docs/NETCONVERT.html) or [NETGENERATE](https://sumo.dlr.de/docs/NETGENERATE.html),
* A population definition in form of a [statistics file](https://sumo.dlr.de/docs/Demand/Activity-based_Demand_Generation.html) (`stats.xml`), but the only required fields and attributes are:
```
<city>
    <general inhabitants="3500" households="2000"/>
</city>
```

More fields can be specified if desired. RandomActivityGen will generate sane defaults for any missing values and populate the statistics file with streets, city gates, and schools.

**Output:** A complete statistics file (`.stats.xml`) that can be used with ACTIVITYGEN.

Use `--help` to see all parameters.

### Example

The repository contains example networks and statistics files in the `in/` folder for a synthetic example and five Danish cities; Aalborg, Esbjerg, Randers, Slagelse, and Vejen. Note that the Aalborg network is too large for the github repo but can be supplied upon demand.

Running RandomActivityGen with default parameters:
```
python randomActivityGen.py --net-file=in/example.net.xml --stat-file=in/example.stat.xml --output-file=out/result.stat.xml
``` 

The resulting `out/result.stats.xml` can be used with ACTIVITYGEN as follows:
```
"$SUMO_HOME/bin/activitygen" --net-file=in/example.net.xml --stat-file=out/result.stat.xml --output-file=out/result.trips.rou.xml --random
```

You now have a `.trips.rou.xml` file that you can use with a routing tool, for instance [DUAROUTER](https://sumo.dlr.de/docs/DUAROUTER.html).


## Obtaining real-world networks
OpenStreetMaps is a good source for getting real world networks. These need to be converted into SUMO (`.net.xml`) networks before usage in both this tool and for SUMO in general.
Note that the online export-tool of OSM does not allow exporting a network with more than 50000 nodes, at time of writing. However, SUMO provides tools for downloading tiles of a bounding box from OSM, stitching them together, and converting them to a SUMO network. 

Using the following utilities provided by SUMO:
```
# Get the osm network from the given coordinates, Aalborg, Denmark chosen here
$SUMO_HOME/tools/osmGet.py -b 9.8012,56.9581,10.0765,57.1142 --prefix aalborg
# Builds a SUMO network from the given osm network
$SUMO_HOME/tools/osmBuild.py --osm-file aalborg-metro_bbox.osm.xml --prefix aalborg
```

## Testing
This tool is developed during a bachelors project which results in a paper. Therefore, testing is a large part of the effort. 
Source code for these tests is found under `testing/` as Python scripts. Documentation exists in the source code for the interested reader but generally each script can simply be run and it will output the results and draw any plots. 

### School testing
Two ways of testing school placement has been implemented; assignment divergence and KS-tests. The latter are executed in a mixture of Matlab and R.

Assignment divergence testing can be configured to be made on the basis of one or more runs, be visualised or not, and have different bounds defined. 

### City gates
City gates are tested by comparing how many generated gates are placed on an edge where a real city gate is. The
real city gates can be found in `stats/`. A Student's t-test is performed on the number of correctly placed city gates.

### Population and industry density
Population and industry density was tested by comparison with trips created by `randomTrips.py` and the traffic from the [LuST](https://github.com/lcodeca/LuSTScenario) scenario.
