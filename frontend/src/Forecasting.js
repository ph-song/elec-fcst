import { Button, FileInput, H1, H2} from "@blueprintjs/core";
import { useState, useEffect} from "react";
import './App.css';

import axios from "axios";

import { Line } from 'react-chartjs-2';
import Chart from 'chart.js/auto';
import 'chartjs-adapter-date-fns';


function Forecasting() {

  const [file, setFile] = useState()
  const [fileName, setFileName] = useState()


  const [chartData, setChartData] = useState({datasets: [{data: [],},],});
  const [options, setOptions]  = useState({scales: {x: {},y: {},}});
  
  useEffect( () => {

    axios({
      url:'http://localhost:888/',
      method: 'get'
    })
    .then((response) =>{
      console.log(response.data)

      const labels1 = response.data.actual.map((item) => new Date(item.time));
      const values1 = response.data.actual.map((item) => item.load_kw/1000);
      const result1 = labels1.map((value, index) => ({ x: value, y: values1[index] }));

      const labels2 = response.data.predict.filter(item => 'xgb_load1' in item).map(item => new Date(item['time']))
      const values2 = response.data.predict.filter(item => 'xgb_load1' in item).map(item=>item['xgb_load1'])
      const result2 = labels2.map((value, index) => ({ x: value, y: values2[index]/1000}));

      const labels3 = response.data.predict.filter(item => 'lgb_load1' in item).map(item => new Date(item['time']))
      const values3 = response.data.predict.filter(item => 'lgb_load1' in item).map(item=>item['lgb_load1'])
      const result3 = labels3.map((value, index) => ({ x: value, y: values3[index]/1000}));

      const chartData = {
        //labels: labels,
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
      
      const options = {
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
      
      setOptions(options);
      setChartData(chartData);  //*/
      })
      .catch((error) => {
        console.error('Error fetching data:', error);
      });
    }, [])


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
    const data = new FormData()
    data.append('zip_file', file)//req.fil
    axios({
      url:"http://localhost:888/upload",
      method:"post",
      data: data
    })
    .then(function(res){
      alert(res)
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

          <H1 className="">Electricity Demand</H1>

          <div className="" style={{position: "relative", height:"45vh", width:"90vw"}}>
            <Line data={chartData} options={options}/>
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