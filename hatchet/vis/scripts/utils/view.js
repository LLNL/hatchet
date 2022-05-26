import { makeSignaller } from "../cct/cct_globals";

class View{
    constructor(elem, model){
        this.elem = elem;
        this.model = model;
        this.observers = makeSignaller();
    }

    register(s){
        this.observers.add(s, this.constructor.name);
    }

    renderer(){
        /**
         * Returns a function which can be used as a
         * callback and have 'this' available
         */
        return () => {
            this.render();
        }
    }
}

export default View;