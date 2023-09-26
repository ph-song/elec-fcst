import { Button, ButtonGroup, FileInput, H1, H2, H3} from "@blueprintjs/core";
import { useState, useEffect} from "react";
import './App.css';

import axios from "axios";

import { Line } from 'react-chartjs-2';
import Chart from 'chart.js/auto';
import 'chartjs-adapter-date-fns';

import { ColorRing } from  'react-loader-spinner'

function Forecasting() {
  const [file, setFile] = useState(null)
  const [fileName, setFileName] = useState()

  const [isLoading, setIsLoading] = useState(false)

  const [chartData1, setChartData1] = useState({datasets: [{data: [],},],});
  const [options1, setOptions1]  = useState({scales: {x: {},y: {},}});

  const [chartData2, setChartData2] = useState({datasets: [{data: [],},],});
  const [options2, setOptions2]  = useState({scales: {x: {},y: {},}});
  
  //whenever page is loaded
  useEffect( () => {
    axios({
      url:'http://localhost:888/',
      method: 'get'
    })
    .then((response) =>{
      console.log(response.data)

      //model prediction
      const labels = response.data.actual.map((item) => new Date(item.time));
      const values = response.data.actual.map((item) => item.load_kw/1000);
      const result = labels.map((value, index) => ({ x: value, y: values[index] }));
      
      const resultPredXGB = parseData(response.data.predict, 'xgb_load')
      const resultPredLGB = parseData(response.data.predict, 'lgb_load')
      const resultPredCTB = parseData(response.data.predict, 'cat_load')
      const resultPredNaive48 = parseData(response.data.predict, 'n48_load')
      const resultPredNaive168 = parseData(response.data.predict, 'n168_load')

      const chartData1 = {
        labels: labels,
        datasets: [
          {
            label: 'Electricity Demand',
            data: result
          },
          {
            label: 'XGBoost',
            data: resultPredXGB
          },
          {
            label: 'LightGBM',
            data: resultPredLGB
          },
          {
            label: 'CatBoost',
            data: resultPredCTB
          },
          {
            label: 'Naive',
            data: resultPredNaive48
          },
          {
            label: 'Seasonal Naive',
            data: resultPredNaive168
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
      const resultErrXGB = parseData(response.data.predict, 'xgb_error')
      const resultErrLGB = parseData(response.data.predict, 'lgb_error')
      const resultErrCTB = parseData(response.data.predict, 'cat_error')
      const resultErrNaive48 = parseData(response.data.predict, 'n48_error')
      const resultErrNaive168 = parseData(response.data.predict, 'n168_error')

      const chartData2 = {
        labels: labels,
        datasets: [
          {
            label: 'XGBoost',
            data: resultErrXGB
          },
          {
            label: 'LightGBM',
            data: resultErrLGB
          },
          {
            label: 'CatBoost',
            data: resultErrLGB
          },
          {
            label: 'Naive',
            data: resultErrNaive48
          },
          {
            label: 'Seasonal Naive',
            data: resultErrNaive168
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

  //when a file is uploaded 
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

  //when upload button is pressed
  const handleUpload = (e)=>{
    setIsLoading(true)
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
      setIsLoading(false)
      window.location.reload(false)
    })
    .catch(function(err){
      setIsLoading(false)
      alert(err.response.data.msg)
      e.preventDefault()
    })
  }


    return (
      <div className="container">
        
        <H1>Electricity Demand</H1>

        <div className='row' style={{position: "relative",height:"45vh",  width:"90vw"}}>
          <H3>Forecast</H3>
          <Line data={chartData1} options={options1}/>
        </div>

        <div className='row'>
          <H3>Data Upload</H3>
          <FileInput className='col-xs-10 col-md-6' fill={false} text={fileName} onInputChange={handleFile} large={true}/>
          <Button className='col-xs-2' onClick={handleUpload} disabled= {isLoading} large={true}> upload </Button>
        </div>

        <div className='row' style={{position: "relative", height:"45vh", width:"90vw"}}>
          <H3>Model Error</H3>
          <Line data={chartData2} options={options2}/>
        </div>

        <div className='row' 
          style={{position: 'absolute',top: '50%',left: '50%',
          transform: 'translate(-50%, -50%)',zIndex: 9999}}
          >
          <ColorRing
            visible={isLoading}
            height="150"
            width="150"
            ariaLabel="blocks-loading"
            wrapperStyle={{}}
            wrapperClass="blocks-wrapper"
            colors={['#e15b64', '#f47e60', '#f8b26a', '#abbd81', '#849b87']}
          />
        </div>
          
      </div>
    );
  }
  
  export default Forecasting;