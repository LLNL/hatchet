const HtmlWebpackPlugin = require('html-webpack-plugin');
const path = require('path');

module.exports = {
    module:{
        rules:[
            {
                test: /\.css$/i,
                use: ["style-loader", "css-loader"]
            },
            {
                test: /\.(js|jsx)$/,
                exclude: /node_modules/,
                loader: 'babel-loader',
                options:{
                    cwd: path.resolve(__dirname),
                    presets:["@babel/preset-env"]
                }
            }
        ]
    },
    entry: {
        cct: [path.resolve(__dirname,'scripts/cct.js')],
    },
    output: {
        publicPath: path.resolve(__dirname, 'static'),
        filename: '[name]_bundle.js',
        path: path.resolve(__dirname, 'static')
    },
    optimization: {
        minimize: false
    },
    plugins:[
        new HtmlWebpackPlugin({
            chunks: ['cct'],
            filename: 'cct_bundle.html'
        })
    ],
    mode: 'production'
}