import { Button, FileInput, H1, H2} from "@blueprintjs/core";
import { useState, useEffect} from "react";
import { UserData } from "./data.js";
import './App.css';
import { Line } from 'react-chartjs-2';
import Chart from 'chart.js/auto';
import axios from "axios";

function Forecasting() {

  const [data, setData] = useState()
  const [file, setFile] = useState()

  const [userData, setUserData] = useState({
    labels: UserData.map((data) => data.Time),
    datasets: [
      {
        label: "Electricity demand",
        data: UserData.map((data) => data.Load/1000)
    }
    ],
  });

  const handleFile = (e)=>{
    if (e.target.files[0].type !== 'text/csv'){
        alert("wrong file format")
        return
    }else{
        setFile(e.target.files[0]);
        console.log(123)
    }
  }

  const handleUpload = (e)=>{
    const data = new FormData()
    data.append('uploadcsv', file)//req.file

    axios({
      url:"http://localhost:888/upload",
      method:"post",
      data: data
    })
    .then(function(res){
      alert(res.data.msg)
      window.location.reload(false)
    })
    .catch(function(err){
      alert(err.response.data.msg)
      e.preventDefault()
    })
  }


  useEffect(() =>{
    axios({
      url:'http://localhost:888/',
      method: 'get'
    })
    .then(function(res){
      if (res.status === 200){
        setData(res.data)
      }
    })
    .catch(function(err){
      console.log('error')
    })
  })



    return (
      <div className="container">

        <div className= ''>

          <H1 className="">Electricity Demand</H1>

          <div className="" style={{position: "relative", height:"45vh", width:"90vw"}}>
            <Line data={userData} />
          </div>

          <H2 className=''>Data Upload</H2>

          <div className='row'>

            <FileInput className='col-xs-10' fill={false}  onInputChange={handleFile} large={true}/>
            
            <Button className='col-xs-2' onClick={handleUpload} large={true}> upload </Button>
          </div>
          
        </div>

      </div>
    );
  }
  
  export default Forecasting;