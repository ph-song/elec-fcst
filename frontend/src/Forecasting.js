import { Button, FileInput, H1, H2} from "@blueprintjs/core";
import { useState, useEffect} from "react";
import './App.css';

import axios from "axios";

import { Line } from 'react-chartjs-2';
import Chart from 'chart.js/auto';
import 'chartjs-adapter-date-fns';


function Forecasting() {

  const [file, setFile] = useState(null)
  const [fileName, setFileName] = useState()

  const [chartData1, setChartData1] = useState({datasets: [{data: [],},],});
  const [options1, setOptions1]  = useState({scales: {x: {},y: {},}});

  const [chartData2, setChartData2] = useState({datasets: [{data: [],},],});
  const [options2, setOptions2]  = useState({scales: {x: {},y: {},}});
  
  useEffect( () => {

    axios({
      url:'http://localhost:888/',
      method: 'get'
    })
    .then((response) =>{
      console.log(response.data)

      //model prediction
      const labels1 = response.data.actual.map((item) => new Date(item.time));
      const values1 = response.data.actual.map((item) => item.load_kw/1000);
      const result1 = labels1.map((value, index) => ({ x: value, y: values1[index] }));
      
      const result2 = parseData(response.data.predict, 'xgb_load')
      const result3 = parseData(response.data.predict, 'lgb_load')

      const chartData1 = {
        labels: labels1,
        datasets: [
          {
            label: 'Electricity Demand',
            data: result1
          },
          {
            label: 'XGBoost',
            data: result2
          },
          {
            label: 'LightGBM',
            data: result3
          }
        ],
      };
      
      const options1 = {
        scales: {
          x: {
            type: 'time', time:{unit: 'day'},
            title: {
              display: true,
              text: 'Time', // Customize the y-axis label here
            }
          },
          y: {
            ticks:{beginAtZero: true, min:0},
            title: {
              display: true,
              text: 'Load (MW)', // Customize the y-axis label here
            },
          },
        },
      };
      
      setOptions1(options1);
      setChartData1(chartData1);  //*/

      //model error
      const result4 = parseData(response.data.predict, 'xgb_error')
      const result5 = parseData(response.data.predict, 'lgb_error')

      const chartData2 = {
        labels: labels1,
        datasets: [
          {
            label: 'XGBoost',
            data: result4
          },
          {
            label: 'LightGBM',
            data: result5
          }
        ],
      };
      
      const options2 = {
        scales: {
          x: {
            type: 'time', time:{unit: 'day'},
            title: {
              display: true,
              text: 'Time', // Customize the y-axis label here
            }
          },
          y: {
            ticks:{beginAtZero: true, min:0},
            title: {
              display: true,
              text: 'Absolute Error (MW)', // Customize the y-axis label here
            },
          },
        },
      };
      
      setOptions2(options2);
      setChartData2(chartData2);  //*/

      })
      .catch((error) => {
        console.error('Error fetching data:', error);
      });
    }, [])

  function parseData(data, key){
    const labels = data.filter(item => key in item && item[key] > 0).map(item => new Date(item['time']))
    const values = data.filter(item => key in item && item[key] > 0).map(item=>item[key])
    const result = labels.map((value, index) => ({ x: value, y: values[index]/1000}));
    return result
  }

  const handleFile = (e)=>{
    const file = e.target.files[0]
    if (file.type !== 'application/zip'){
        alert("wrong file format")
        setFileName()
        return
    }else{
      setFileName(file.name)
      setFile(file);
    }
  }

  const handleUpload = (e)=>{
    if (file === null){
      alert("please upload file")
      return 
    }
    const data = new FormData()
    data.append('zip_file', file)//req.fil
    axios({
      url:"http://localhost:888/upload",
      method:"post",
      data: data
    })
    .then(function(res){
      alert('file uploaded')
      window.location.reload(false)
    })
    .catch(function(err){
      alert(err.response.data.msg)
      e.preventDefault()
    })
  }


    return (
      <div className="container">

        <div className= ''>

          <H2 className="">Electricity Demand</H2>

          <div className="" style={{position: "relative", height:"45vh", width:"90vw"}}>
            <Line data={chartData1} options={options1}/>
          </div>

          <H2 className="">Model Error</H2>

          <div className="" style={{position: "relative", height:"45vh", width:"90vw"}}>
            <Line data={chartData2} options={options2}/>
          </div>

          <H2 className=''>Data Upload</H2>

          <div className='row'>

            <FileInput className='col-xs-10' fill={false} text={fileName} onInputChange={handleFile} large={true}/>
            
            <Button className='col-xs-2' onClick={handleUpload} large={true}> upload </Button>
          </div>
          
        </div>

      </div>
    );
  }
  
  export default Forecasting;