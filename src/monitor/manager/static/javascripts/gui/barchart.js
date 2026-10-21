class BarChart {

    constructor(elementId, items) {

        this.scale = 1.0;
        this.precision = 1;
        this.element = document.getElementById(elementId);

        this.barHeight = this.element.clientHeight - 30;

        this.div = document.createElement("div");
        this.div.className = "barchart";
        this.div.style.display = "flex";
        this.div.style.flexDirection = "row";
        this.div.style.alignItems = "flex-end";
        this.div.style.height = "180px";

        this.chart = []

        for (var iItem = 0; iItem < items; iItem++) {

            this.column = document.createElement("div");

            this.column.style.flexDirections = "column";

            var title = document.createElement("label");
            var label = document.createElement("label");

            label.style = "display:block; overflow: hidden; margin-top: 2px; text-overflow: ellipsis white-space: nowrap; width:57px; text-align: center";
            title.style = "display:block; overflow: hidden; text-overflow: ellipsis white-space: nowrap; width:57px; text-align: center";

            title.innerHTML = "0";
            label.innerHTML = `${iItem}`;

            var bar = document.createElement("div");

            bar.style.width = "47px";
            bar.style.height = `0px`;
            bar.style.maxHeight = `160px`;
            bar.style.margin = `0 3px`;
            bar.style.border = "solid 1px black"

            this.column.appendChild(title);
            this.column.appendChild(bar);
            this.column.appendChild(label);

            this.div.appendChild(this.column);

            this.chart.push({
                "title": title,
                "bar": bar
            })

            this.element.append(this.div);

        }

    }

    draw(data, current, highlight, normal, decimals) {

        for (var item = 0; item < data.length; item++) {

            this.chart[item].title.innerHTML = `${(data[item] / this.precision).toFixed(0)}`;
            this.chart[item].bar.style.height = `${data[item] / Math.pow(10, this.scale)}px`;
            this.chart[item].bar.style.backgroundColor = (current == item ? highlight : normal);

        }

    }

    setOptimumScale(data) {

        function calculate(barHeight, value) {
            var scale = 1;

            for (; (Math.pow(10, scale) * barHeight) <= value; scale += 1);
           
            var precision = Math.log(value) * Math.LOG10E + 1 | 0;  // for positive integers

            precision = precision < 5 ? 1 : Math.pow(10, precision - 5); 

            return {
                scale: scale,
                precision : precision
            }


        }

        this.scale = 1;  
        this.precision = 1;

        for (var item = 0; item < data.length; item++) {

            if (data[item] != 0) {
                var calculation = calculate(this.barHeight, data[item]);
                
                this.precision = calculation.precision > this.precision ? calculation.precision : this.precision;
                this.scale = calculation.scale > this.scale ? calculation.scale : this.scale;

            }

        }

    }

}
