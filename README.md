# RandomActivityGen

This tool provides an easy way to generate semi-realistic traffic demand for [SUMO](http://sumo.sourceforge.net/) by generating a population statistics file (`.stats.xml`) for [ACTIVITYGEN](https://sumo.dlr.de/docs/ACTIVITYGEN.html).

RandomActivityGen works best for city networks, and works very well with a random [NETGENERATE](https://sumo.dlr.de/docs/NETGENERATE.html) network.  

## Usage

**Required input:**

* A network file (`.net.xml`) as generated via [NETCONVERT](https://sumo.dlr.de/docs/NETCONVERT.html) or [NETGENERATE](https://sumo.dlr.de/docs/NETGENERATE.html),
* A population definition in form of a [statistics file](https://sumo.dlr.de/docs/Demand/Activity-based_Demand_Generation.html) (`stats.xml`), but the only required fields and attributes are:
```
<city>
    <general inhabitants="3500" households="2000"/>
</city>
```

More fields can be specified if desired. RandomActivityGen will generate any missing values and populate the statistics file with streets, city gates, and schools.

**Output:** A complete statistics file (`.stats.xml`) that can be used with ACTIVITYGEN.

### Example

The repository contains an example network and almost empty statistics file in the `in/` folder. Use RandomActivityGen with default parameters:
```
python randomActivityGen.py --net-file=in/example.net.xml --stat-file=in/example.stat.xml --output-file=out/result.stat.xml
``` 

The resulting `out/result.stats.xml` can be used with ACTIVITYGEN as follows:
```
"$SUMO_HOME/bin/activitygen.exe" --net-file=in/example.net.xml --stat-file=out/result.stat.xml --output-file=out/result.trips.rou.xml --random
```

You now have a `.trips.rou.xml` file that you can use with a routing tool, for instance [DUAROUTER](https://sumo.dlr.de/docs/DUAROUTER.html).