import {d3, globals} from './cct_globals';
import Stats from './cct_stats';
import { hierarchy as d3v7_hierarchy } from 'd3-hierarchy';

class Forest{

    constructor(cct_forest_def){
        //initialize forest containers
        this.immutableTrees =  [];
        this.mutableTrees = [];

        //initialize forest descriptors
        this.numberOfTrees = cct_forest_def.length;
        this.metricColumns = d3.keys(cct_forest_def[0].metrics);
        this.attributeColumns = d3.keys(cct_forest_def[0].attributes);
        this.aggregateMinMax = {};
        
        this.maxHeight = 0;
        this.forestMinMax = {};
        this.forestMetrics = [];
        this.rootNodeNames = [];

        this.stats = new Stats();
        this.zeroes = false;

        //setup functions
        this.instantiateTrees(cct_forest_def);
        this.organizeMetrics(cct_forest_def);

    }

    instantiateTrees(forestData){
        /**
         * Create trees as a collection of d3 hierarchies
         */
        let offset = 0;

        for (let treeIndex = 0; treeIndex < forestData.length; treeIndex++) {
            let hierarchy = d3v7_hierarchy(forestData[treeIndex], d => d.children);
            hierarchy.size = hierarchy.descendants().length;

            //add a surrogate id if _hatchet_nid is not present
            if(!Object.keys(hierarchy.descendants()[0].data.metrics).includes("_hatchet_nid")){
                hierarchy.descendants().forEach(function(d, i){
                    if(d.data.metrics !== undefined){
                        d.data.metrics.id = offset+i;
                    }
                    else{
                        d.data.id = offset+i;
                    }
                })
                offset += hierarchy.size;
            }

            this.immutableTrees.push(hierarchy);
            this.mutableTrees.push(hierarchy);

            if (this.immutableTrees[treeIndex].height > this.maxHeight){
                this.maxHeight = this.immutableTrees[treeIndex].height;
            }
        }

        //sort in descending order
        this.immutableTrees.sort((a,b) => b.size - a.size);
        this.mutableTrees.sort((a,b) => b.size - a.size);
    }


    organizeMetrics(forestData){
        /**
         * Setup the metrics across the forest 
         */

        //get the max and min metrics across the forest
        // and for each individual tree
        var _forestMetrics = [];
        var _forestMinMax = {}; 


        //inital metric columns setup
        for(var metric = 0; metric < this.metricColumns.length; metric++){
            let metricName = this.metricColumns[metric];
            //remove private metric
            if(this.metricColumns[metric][0] == '_'){
                this.metricColumns.splice(metric, 1);
            }
            else{
                //setup aggregrate min max for metric
                this.aggregateMinMax[metricName] = {min: Number.MAX_VALUE, max: Number.MIN_VALUE};
            }
        }

        //setup repository of metrics across trees and forest
        for (var index = 0; index < this.numberOfTrees; index++) {
            var thisTree = forestData[index];
            let mc = this.metricColumns;

            // Get tree names for the display select options
            this.rootNodeNames.push(thisTree.frame.name);

            var thisTreeMetrics = {};

            for (var j = 0; j < mc.length; j++) {
                thisTreeMetrics[mc[j]] = {};
                thisTreeMetrics[mc[j]]["min"] = Number.MAX_VALUE;
                thisTreeMetrics[mc[j]]["max"] = Number.MIN_SAFE_INTEGER;

                //only one run time
                if(index == 0){
                    _forestMinMax[mc[j]] = {};
                    _forestMinMax[mc[j]]["min"] = Number.MAX_VALUE;
                    _forestMinMax[mc[j]]["max"] = Number.MIN_SAFE_INTEGER;
                }
            }

            this.immutableTrees[index].each(function (d) {
                for (var i = 0; i < mc.length; i++) {
                    var tempMetric = mc[i];
                    thisTreeMetrics[tempMetric].max = Math.max(thisTreeMetrics[tempMetric].max, d.data.metrics[tempMetric]);
                    thisTreeMetrics[tempMetric].min = Math.min(thisTreeMetrics[tempMetric].min, d.data.metrics[tempMetric]);
                    _forestMinMax[tempMetric].max = Math.max(_forestMinMax[tempMetric].max, d.data.metrics[tempMetric]);
                    _forestMinMax[tempMetric].min = Math.min(_forestMinMax[tempMetric].min, d.data.metrics[tempMetric]);
                }
            });

            _forestMetrics.push(thisTreeMetrics);
        }
        this.forestMetrics = _forestMetrics;

        // Global min/max are the last entry of forestMetrics;
        this.forestMinMax = _forestMinMax;
        this.forestMetrics.push(_forestMinMax);
    }


    _setZeroFlags(h, primaryMetric){
        //runs on default
        h.each(function(node){
            var metric = node.data.metrics[primaryMetric];
            if(metric != 0){
                node.data.show = 1;
            }
            else{
                node.data.show = 0;
            }
        })
    }

    _setOutlierFlags(h, primaryMetric, currentStrictness){
        /**
         * Sets outlier flags on a d3 hierarchy of call sites.
         * An outlier is defined as outside of the range between
         * the IQR*(a user defined scalar) + 75th quantile and
         * 25th quantile - IQR*(scalar). 
         * 
         * @param {Hierarchy} h - A d3 hierarchy containg metric values
         */
        var outlierScalar = currentStrictness;
        var upperOutlierThreshold = Number.MAX_VALUE;
        var lowerOutlierThreshold = Number.MIN_VALUE;

        var metrics = this._getListOfMetrics(h, primaryMetric);
        var IQR = this.stats._getIQR(metrics, primaryMetric);

        if(!isNaN(IQR)){
            upperOutlierThreshold = this.stats._quantile(metrics, .75, primaryMetric) + (IQR * outlierScalar);
            lowerOutlierThreshold = this.stats._quantile(metrics, .25, primaryMetric) - (IQR * outlierScalar);
        } 

        h.each(function(node){
            var metric = node.data.metrics[primaryMetric];
            if( metric >= upperOutlierThreshold || 
                metric <= lowerOutlierThreshold){
                node.data.show = 1;
            }
            else{
                node.data.show = 0;
            }
        })
    }

    _getAggregateMetrics(h, aggFunct){
        /**
         * Utility function which gets aggregrate metrics for
         * a subtree.
         * 
         * @param {Hierarchy} h - A d3 hierarchy containing metrics
         */
        let agg = {};
        
        for(let metric of this.metricColumns){
            switch (aggFunct){
                // Aggregation Options: Average vs. Sim
                case globals.AVG:
                    if(!metric.includes("(inc)")){
                        h.sum(d=>{
                            if(d.aggregateMetrics){
                                return d.aggregateMetrics[metric];
                            } else{
                                return d.metrics[metric];
                            }
                        });

                        agg[metric] = h.value/h.copy().count().value;
                    }
                    else{
                        agg[metric] = h.data.metrics[metric];
                    }
                    break;
                case globals.SUM:
                    if(!metric.includes("(inc)")){
                        h.sum(d=>{    
                            if(d.aggregateMetrics){
                                return d.aggregateMetrics[metric];
                            } else{
                                return d.metrics[metric];
                            }
                        });
                        agg[metric] = h.value;
                    }
                    else{
                        agg[metric] = h.data.metrics[metric];
                    }
                    break;
                default:
                    console.warn(`${aggFunct} is not supported for aggregating subtrees.`)
            }
        }

        return agg;
    }

    _getSubTreeDescription(h){
        /**
         * A utility function which returns a description of a subtree in terms
         * height, and number of nodes.
         * **TODO** - Add other descriptive details
         *
         * @param {Hierarchy} h - A d3 hierarchy containing metrics
         */
        let desc = {};

        desc.height = h.height;
        desc.size = h.count().value;
        
        return desc;
    }

    _buildDummyHolder(protoype, parent, elided){
        /**
         * A function that builds a surrogate node from a
         * prototype node and the parent associated with that
         * prototype.
         * 
         * @param {Node} prototype - A node which are going to replace with the resulting surrogate node
         *      A prototype is used here to preserve the descriptive stats of the removed node
         * @param {Node} parent - A node we are linking the new surrogate node to
         * @param {Node} elided - A list of sibling nodes which this surrogate is eliding from view
         */
        var dummyHolder = null;
        var aggregateMetrics = {};
        var description = {
            maxHeight: 0,
            minHeight: Number.MAX_VALUE,
            size: 0,
            elidedSubtrees:0
        };


        dummyHolder = protoype.copy();
        dummyHolder.depth = protoype.depth;
        dummyHolder.height = protoype.height;
        dummyHolder.children = null;

        //need a better way to make elided happen
        // pass in as arg makes sense
        dummyHolder.elided = elided;
        dummyHolder.dummy = true;
        dummyHolder.aggregate = false;
        dummyHolder.parent = parent;
        dummyHolder.outlier = 0;
        

        //initialize the aggregrate metrics for summing
        for(let metric of this.metricColumns){
            aggregateMetrics[metric] = 0;
        }

        for(let elided of dummyHolder.elided){
            var aggMetsForChild = this._getAggregateMetrics(elided, globals.AVG);
            var descriptionOfChild = this._getSubTreeDescription(elided);
            
            for(let metric of this.metricColumns){
                aggregateMetrics[metric] += aggMetsForChild[metric];
            }

            description.size += descriptionOfChild.size;

            if(descriptionOfChild.height > description.maxHeight){
                description.maxHeight = descriptionOfChild.height;
            }

            if(descriptionOfChild.height < description.minHeight){
                description.minHeight = descriptionOfChild.height;
            }

        }

        description.elidedSubtrees = elided.length;

        //get the overall min and max of aggregate metrics
        // for scales
        for(let metric of this.metricColumns){
            if (aggregateMetrics[metric] > this.aggregateMinMax[metric].max){
                this.aggregateMinMax[metric].max = aggregateMetrics[metric];
            }
            if(aggregateMetrics[metric] < this.aggregateMinMax[metric].min){
                this.aggregateMinMax[metric].min = aggregateMetrics[metric];
            }
        }

        dummyHolder.data.aggregateMetrics = aggregateMetrics;
        dummyHolder.data.description = description;

        //more than sum 0 nodes were aggregrated
        // together
        dummyHolder.aggregate = true;

        return dummyHolder;
    }

    _pruningVisitor(root, condition, metric){
        /**
         * A recursive function that scans nodes for
         *  the existance of an outlier flag and manages the
         *  removal of non-outlier nodes in addition to the 
         *  creation of surrogate nodes that hold aggregated
         *  data.
         * 
         *  Note - The processing is done on the children of root primarily.
         *  
         *  @param {Hierarchy} root - Or current root node in our recursive scanning and modification of trees.
         *  @param {Number} condition - The comparision condition which our node value is compared against
         */

        if(root.children){
            var dummyHolder = null;
            var elided = [];
            
            for(var childNdx = root.children.length-1; childNdx >= 0; childNdx--){
                let child = root.children[childNdx];
                //clear dummy node codition so it
                // doesnt carry on between re-draws
                child.data.dummy = false;

                //condition where we remove child
                if(child.value < condition){
                    if(!root._children){
                        root._children = [];
                    }

                    elided.push(child);
                    root._children.push(child);
                    root.children.splice(childNdx, 1);
                }
            } 
            
            
            if (root._children && root._children.length > 0){
                dummyHolder = this._buildDummyHolder(elided[0], root, elided);
                root.children.push(dummyHolder);
            }

            for(let child of root.children){
                this._pruningVisitor(child, condition, metric);
            }

            if(root.children.length == 0){
                root.children = null;
            }
        }
    }

    _setDisplayFlags(flagOp, t, primaryMetric, currentStrictness){
        if(flagOp == "FlagZeros"){
            this._setZeroFlags(t, primaryMetric);
        }
        else if(flagOp == "FlagOutliers"){
            this._setZeroFlags(t, primaryMetric);
            this._setOutlierFlags(t, primaryMetric, currentStrictness);
        }
        else if(flagOp == "FlagRange"){
            this._setZeroFlags(t, primaryMetric);
            this._setRangeFlags(t, primaryMetric, inclusiveRange);
        }

    }

    aggregateTreeData(primaryMetric, currentStrictness, op){
        /**
         * Helper function which drives the outlier
         * detection and pruning of a fresh tree.
         * This function creates a fresh hierarchy when called and
         * overwrites the current tree in the view.
         */
        let newTrees = this.getFreshTrees();

        for(let i in newTrees){
            let t = newTrees[i];
            if(currentStrictness > -1){
                this._setDisplayFlags(op, t, primaryMetric, currentStrictness);

                //The sum ensures that we do not prune 
                //away parent nodes of identified outliers.
                t.sum(d => d.show);
                this._pruningVisitor(t, 1, primaryMetric);

                //update size of subtrees on the nodes
                t.size = t.descendants().length;
                
            }

            this.mutableTrees[i] = t;
        }
    }

    _getListOfMetrics(h, primaryMetric){
        //Gets a list of metrics with 0s removed
        // 0s in hpctoolkit are too numerous and they
        // throw off outlier calculations
        var list = [];
        
        h.each(d=>{
            if(d.data.metrics[primaryMetric] != 0){
                list.push(d.data.metrics)
            }
        })

        return list;
    }

    getFreshTrees(){
        let mutableTrees = [];

        for(let tree of this.immutableTrees){
            mutableTrees.push(tree.copy());
        }

        return mutableTrees;
    }

    getTrees(){
        return this.mutableTrees;
    }

    getCurrentTree(index){
        return this.mutableTrees[index];
    }
    
    setCurrentTree(index, tree){
        this.mutableTrees[index] = tree; 
    }

}

export default Forest;