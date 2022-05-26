class Stats{

    _asc(arr, metric){
        /**
         *  Sorts an array in ascending order.
         */
        
        return arr.sort((a,b) => a[metric]-b[metric])
    }
    
    _quantile(arr, q, metric){
        /**
         * Gets a particular quantile from an array of numbers
         * 
         * @param {Array} arr - An array of floats
         * @param {Number} q - An float between [0-1] represening the quantile we want 
         */
        const sorted = this._asc(arr, metric);
        const pos = (sorted.length - 1) * q;
        const base = Math.floor(pos);
        const rest = pos - base;
        if (sorted[base + 1] !== undefined) {
            return sorted[base][metric] + rest * (sorted[base + 1][metric] - sorted[base][metric]);
        } else {
            return sorted[base][metric];
        }
    }

    _getIQR(arr, metric){
        /**
         * Returns the interquartile range for a an array of numbers
         */
        if(arr.length != 0){
            var q25 = this._quantile(arr, .25, metric);
            var q75 = this._quantile(arr, .75, metric);
            var IQR = q75 - q25;
            
            return IQR;
        }
        
        return NaN;
    }
}

export default Stats;