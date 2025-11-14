const path = require("path");
const webpack = require("webpack");

module.exports = {
  entry: "./src/index.js",

  output: {
    path: path.resolve(__dirname, "./static/frontend"),
    filename: "[name].js",
    publicPath: "/",  // ← ważne!
  },

  resolve: {
    extensions: [".js", ".jsx"],
  },

  module: {
    rules: [
      {
        test: /\.(js|jsx)$/,
        exclude: /node_modules/,
        use: {
          loader: "babel-loader",
          options: {
            presets: ["@babel/preset-env", "@babel/preset-react"],
          },
        },
      },
      {
        test: /\.css$/i,
        use: ["style-loader", "css-loader"],
      },
      {
        test: /\.(png|jpe?g|gif|svg)$/i,
        type: "asset/resource",
        generator: {
          filename: "images/[name][ext][query]",
        },
      },
    ],
  },

  devServer: {
    static: {
      directory: path.join(__dirname, "./static/frontend"),
    },
    port: 8080,
    hot: true,
    historyApiFallback: true,
  },

  optimization: {
    minimize: false,
  },

  plugins: [
    new webpack.DefinePlugin({
      "process.env.NODE_ENV": JSON.stringify("development"),
    }),
  ],
};
