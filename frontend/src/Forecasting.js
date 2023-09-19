import { Button, FileInput, H1, H2} from "@blueprintjs/core";
import { useState, useEffect} from "react";
import './App.css';
import { Line } from 'react-chartjs-2';
import Chart from 'chart.js/auto';
import axios from "axios";

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
      const labels = response.data.actual.map((item) => item.time);
      const values1 = response.data.actual.map((item) => item.load_kw/1000);
    

      // Create a Chart.js-compatible data structure
      const chartData = {
        labels: labels,
        datasets: [
          {
            label: 'Electricity Demand',
            data: values1
          }
        ],
      };
      
      const options = {
        scales: {
          x: {
            title: {
              display: true,
              text: 'Time', // Customize the y-axis label here
            }
          },
          y: {
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