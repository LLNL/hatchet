import { globals} from "./cct_globals";

class Controller{
    /**
     * Handles interaction and events by taking requests from the view
     * and firing off functions in the model.
     */
    constructor(model){
        this.model = model;
    }

    dispatcher(){
        return (evt) => {

            // All types of events run through a central dispatch
            // function. The dispatch function decides what to do.
            switch(evt.type) {
                case(globals.signals.UPDATESELECTED):    
                    this.model.updateSelected(evt.nodes);
                    break;
                case (globals.signals.CLICK):
                    this.model.updateSelected(evt.node);
                    break;
                case (globals.signals.COLLAPSESUBTREE):
                    this.model.handleDoubleClick(evt.node);
                    break;
                case(globals.signals.COMPOSEINTERNAL):
                    this.model.handleNodeComposition(evt.node);
                    break;
                case(globals.signals.DECOMPOSENODE):
                    // this.model.handleNodeDecomposition(evt.node);
                    console.log("Decompose coming soon.")
                    break;
                case(globals.signals.TOGGLEBRUSH):
                    this.model.toggleBrush();
                    break;
                case (globals.signals.BRUSH):
                    this.model.setBrushedPoints(evt.selection);
                    break;
                case (globals.signals.METRICCHANGE):
                    this.model.changeMetric(evt.newMetric, evt.source);
                    break;
                case(globals.signals.COLORCLICK):
                    this.model.changeColorScheme(evt.value);
                    break;
                case(globals.signals.TREECHANGE):
                    this.model.updateActiveTrees(evt.display);
                    break;
                case(globals.signals.LEGENDCLICK):
                    this.model.updateLegends(evt.value);
                    break;
                case(globals.signals.ENABLEMASSPRUNE):
                    this.model.enablePruneTree(evt.threshold);
                    break;
                case(globals.signals.REQUESTMASSPRUNE):
                    this.model.pruneTree(evt.threshold);
                    break;
                case(globals.signals.RESETVIEW):
                    this.model.resetView();
                    break;
                case(globals.signals.PRUNERANGEUPDATE):
                    this.model.updatePruneRange(evt.low, evt.high);
                    break;
                case(globals.signals.SNAPSHOT):
                    this.model.storeSnapshotQuery();
                    break;
                case(globals.signals.TOGGLEMENU):
                    this.model.toggleMenuActive();
                    break;
                default:
                    console.warn('Unknown event type', evt.type);
            }
        }
    }
}

export default Controller;