/**
 * Description: Contains the core forest data stucture. 
 *  This datasructure is responsible for all tree related metadata,
 *  magaining the state of trees and providing properly stated trees
 *  back to the model.
 */

import {d3, globals} from './cct_globals';
import Stats from './cct_stats';
import { hierarchy as d3v7_hierarchy } from 'd3-hierarchy';

class Forest{

    constructor(cct_forest_def){
        //initialize forest containers
        this.immutableTrees = [];
        this.prePrunedTrees = [];
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

        this.subtreeMap = {};

        //setup functions
        this.instantiateTrees(cct_forest_def);
        this.organizeMetrics(cct_forest_def);
    }

    hashNode(n){
        return n._hatchet_nid;
    }

    postOrderCheck(t){
        /**
         * Post order check of nodes to identify duplicate subtrees.
         */
        let str = "";
        
        if(t == null)
            return ""
        
        if(t.children !== undefined){
            for(let child of t.children){
                str += this.postOrderCheck(child);
            }
        }

        str += t.data.metrics["time"];
        str += t.data.metrics["time (inc)"];
        str += t.data.metrics["name"];

        if(this.subtreeMap[str] === undefined){
            this.subtreeMap[str] = 0;
        }

        if(this.subtreeMap[str] > 0){
            console.log("Duplicate:", t, this.subtreeMap[str], t.data.metrics._hatchet_nid);
        }

        this.subtreeMap[str] += 1;

        return str;
    }

    findDuplicateSubtrees(){
        /**
         * Wrapper function to idenfity duplicate subtrees.
         */
        for(let t of this.immutableTrees){
            this.postOrderCheck(t);    
        }
    }

    instantiateTrees(forestData){
        /**
         * Create trees as a collection of d3 hierarchies
         */
        let offset = 0;

        for (let treeIndex = 0; treeIndex < forestData.length; treeIndex++) {
            let hierarchy = d3v7_hierarchy(forestData[treeIndex], d => d.children);
            hierarchy.size = hierarchy.descendants().length;

            //add a local nid to this representation
            hierarchy.descendants().forEach(function(d, i){
                d.data.id = offset+i;
            })
            offset += hierarchy.size;

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

    initializePrunedTrees(primaryMetric){
        /**
         * Inializes trees with all zero-subtrees collapsed
         *  into aggregate nodes by default. These are provided
         *  to ensure that intially drawn trees are not overly cluttered
         *  with irrelevant noisy data.
         */
        let newTrees = this.getFreshTrees();

        for(let t in newTrees){
            let pt = this.pruneTree(newTrees[t], primaryMetric, (h, primaryMetric)=>{
                h.each(function(node){
                    var metric = node.data.metrics[primaryMetric];
                    if(metric != 0){
                        node.data.show = 1;
                    }
                    else{
                        node.data.show = 0;
                    }
                })
            });

            pt.size = pt.descendants().length;

            this.prePrunedTrees.push(pt);
            this.mutableTrees[t] = pt;   
        }

        this.prePrunedTrees.sort((a,b) => b.size - a.size);
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
                this.aggregateMinMax[metricName] = {min: Number.MAX_SAFE_INTEGER, max: Number.MIN_SAFE_INTEGER};
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
                thisTreeMetrics[mc[j]]["min"] = Number.MAX_SAFE_INTEGER;
                thisTreeMetrics[mc[j]]["max"] = Number.MIN_SAFE_INTEGER;

                //only one run time
                if(index == 0){
                    _forestMinMax[mc[j]] = {};
                    _forestMinMax[mc[j]]["min"] = Number.MAX_SAFE_INTEGER;
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

    _setPruneFlags(tree, primaryMetric, callback){
        /**
         * Function which evokes an arbitraty callback that sets show
         * flags on the passed tree using the primary metric.
         */
        callback(tree, primaryMetric);
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
                        if(h.aggregateMetrics){
                            return h.aggregateMetrics[metric];
                        }
                        else{
                            h.sum(d=>{
                                return d.metrics[metric];
                            });
                        }
                    }
                    else{
                        agg[metric] = h.data.metrics[metric];
                    }


                    agg[metric] = h.value/h.copy().count().value;
                    break;
                case globals.SUM:
                    if(!metric.includes("(inc)")){
                        if(h.aggregateMetrics){
                            return h.aggregateMetrics[metric];
                        }
                        else{
                            h.sum(d=>{
                                    return d.metrics[metric];
                            });
                        }
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
        dummyHolder.parent = parent;

        dummyHolder.data = {};
        dummyHolder.data.metrics = {};
        dummyHolder.data.metrics._hatchet_nid = protoype.data.metrics._hatchet_nid;
        dummyHolder.data.prototype = protoype;
        dummyHolder.data.elided = elided;
        dummyHolder.data.aggregate = true;
        dummyHolder.outlier = 0;
        

        //initialize the aggregrate metrics for summing
        for(let metric of this.metricColumns){
            aggregateMetrics[metric] = 0;
        }

        for(let elided of dummyHolder.data.elided){
            var aggMetsForChild = this._getAggregateMetrics(elided, globals.SUM);
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

        for(let metric of this.metricColumns){
            aggregateMetrics[metric] = aggregateMetrics[metric]/elided.length;
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
                child.aggregate = false;

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
            

            for(let child of root.children){
                this._pruningVisitor(child, condition, metric);
            }

            if (root._children && root._children.length > 0 && !root.data.aggregate){
                dummyHolder = this._buildDummyHolder(elided[0], root, elided);
                root.children.push(dummyHolder);
            }

            if(root.children.length == 0){
                root.children = null;
            }
        }
    }

    _setDisplayFlags(t, primaryMetric, conditionCallback){
        /**
         * Wrapper function for recursive _setPruneFlags function.
         */
        this._setPruneFlags(t, primaryMetric, conditionCallback);
    }

    pruneTree(t, primaryMetric, conditionCallback){
        /**
         * Takes a tree and prunes it according to the flags
         *  set in setDisplayFlags. The setDisplayFlags sets
         *  flags according to a boolean criteria 
         *  defined in the callback function passed here.
         */

        this._setDisplayFlags(t, primaryMetric, conditionCallback);

        //The sum ensures that we do not prune 
        //away parent nodes of identified outliers.
        t.sum(d => d.show);
        this._pruningVisitor(t, 1, primaryMetric);


        //update size of subtrees on the nodes
        t.size = t.descendants().length;

        return t;
    }

    aggregateTreeData(primaryMetric, conditionCallback){
        /**
         * Helper function which drives the outlier
         * detection and pruning of a fresh tree.
         * This function creates a fresh hierarchy when called and
         * overwrites the current tree in the view.
         */
        let newTrees;

        newTrees = this.getFreshTrees();

        for(let i in newTrees){
            let t = newTrees[i];
            
            t = this.pruneTree(t, primaryMetric, conditionCallback);

            t.each(n=>{
                if(n.data.aggregate == true && n.data.prototype.data.aggregate == true){
                    n.data.prototype = n.data.prototype.data.prototype;
                }
            })
                
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

    resetMutable(){
        /**
         * Resets the mutable trees usable by the model to their initial state.
         */
        if(this.zeroes){
            this.mutableTrees = this.getFreshTrees();
        }
        else{
            this.mutableTrees = this.getPrePrunedTrees();
        }
    }

    getPrePrunedTrees(){
        /**
         * Function which yeilds a new set of pre-pruned trees
         * to the the calling function
         */
        let mutableTrees = [];


        for(let tree of this.prePrunedTrees){
            /**
             * We lose elided and dummy here when we copy.
             */
            let t = tree.copy();
            t.size = t.descendants().length;

            let t_nodes = t.descendants();
            let tree_nodes = tree.descendants();
            for(let i in tree_nodes){
                if(tree_nodes[i].aggregate){
                    t_nodes[i].aggregate = true;
                    t_nodes[i].elided = tree_nodes[i].elided;
                }
                
            }

            mutableTrees.push(t);
        }

        return mutableTrees;
    }

    getFreshTrees(){
        /**
         * Yields a list of un-pruned trees to the calling function.
         */
        let mutableTrees = [];

        for(let tree of this.immutableTrees){
            let t = tree.copy();
            t.size = t.descendants().length;
            mutableTrees.push(t);
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