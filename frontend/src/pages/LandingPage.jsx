import React, { useState, useEffect } from 'react';
import { NavLink } from 'react-router-dom';
import axios from 'axios';
import { UploadCloud, Server, Database, Activity, RefreshCw, Layers, Monitor, HardDrive, Download, CheckCircle, Clock, XCircle } from 'lucide-react';

const API_BASE = 'http://localhost:8000';

const LandingPage = () => {
  const [file, setFile] = useState(null);
  const [opType, setOpType] = useState('resize');
  const [width, setWidth] = useState(400);
  const [height, setHeight] = useState(400);
  const [format, setFormat] = useState('webp');
  const [uploading, setUploading] = useState(false);
  const [activeJob, setActiveJob] = useState(null);

  useEffect(() => {
    let interval;
    if (activeJob && (activeJob.status === 'pending' || activeJob.status === 'processing')) {
      interval = setInterval(async () => {
        try {
          const res = await axios.get(`${API_BASE}/jobs/${activeJob.job_id}`);
          setActiveJob(res.data);
        } catch (err) {
          console.error(err);
        }
      }, 1000);
    }
    return () => clearInterval(interval);
  }, [activeJob]);

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!file) return;
    
    setUploading(true);
    setActiveJob(null);
    const formData = new FormData();
    formData.append('file', file);
    
    let ops = [];
    if (opType === 'resize') {
      ops.push({ type: 'resize', width: parseInt(width), height: parseInt(height) });
    } else {
      ops.push({ type: 'format_convert', target_format: format });
    }
    formData.append('operations', JSON.stringify(ops));

    try {
      const res = await axios.post(`${API_BASE}/jobs`, formData);
      setFile(null);
      // Immediately set the job to start polling
      setActiveJob({ job_id: res.data.job_id, status: 'pending' });
    } catch (err) {
      alert(err.response?.data?.detail || 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  const getStatusIcon = (status) => {
    switch(status) {
      case 'pending': return <Clock className="text-yellow-400" size={24} />;
      case 'processing': return <RefreshCw className="text-primary animate-spin" size={24} />;
      case 'completed': return <CheckCircle className="text-success" size={24} />;
      case 'failed': return <XCircle className="text-danger" size={24} />;
      default: return <Clock className="text-gray-400" size={24} />;
    }
  };

  return (
    <div className="min-h-screen bg-[#0a0a0a] text-white font-sans overflow-x-hidden relative">
      <div className="absolute inset-0 z-0 pointer-events-none opacity-20" 
           style={{ backgroundImage: 'linear-gradient(#333 1px, transparent 1px), linear-gradient(90deg, #333 1px, transparent 1px)', backgroundSize: '40px 40px' }}>
      </div>

      <header className="relative z-10 flex items-center justify-between px-8 py-6 border-b border-[#333] bg-[#0a0a0a]/80 backdrop-blur-md">
        <div className="text-2xl font-black tracking-tighter">IMAGEFLOW</div>
        <nav className="hidden md:flex items-center gap-8 text-sm font-bold tracking-wider">
          <a href="#product" className="hover:text-primary transition-colors">PRODUCT</a>
          <a href="#network" className="hover:text-primary transition-colors">NETWORK</a>
          <NavLink to="/login" className="bg-white text-black px-6 py-2 border-2 border-black hover:bg-transparent hover:text-white hover:border-white transition-all shadow-[4px_4px_0px_#f87171]">
            ADMIN PORTAL
          </NavLink>
        </nav>
      </header>

      <main className="relative z-10">
        <section className="px-8 py-20 max-w-7xl mx-auto flex flex-col md:flex-row items-center gap-16">
          <div className="flex-1 relative">
            <div className="absolute -top-10 -left-10 w-24 h-24 bg-yellow-400 z-0 hidden md:block"></div>
            <div className="relative z-10">
              <h1 className="text-6xl md:text-8xl font-black uppercase leading-[0.9] tracking-tighter mb-2">
                Upload. <br /> Process. <br /> 
                <span className="text-danger">Dominate.</span>
              </h1>
              <p className="mt-8 text-xl font-medium bg-[#1a1a1a] p-4 border-l-4 border-primary max-w-md">
                Distributed power for your image workflows. Let the network handle the heavy lifting.
              </p>
              
              <div className="flex gap-4 mt-8">
                <span className="flex items-center gap-2 border-2 border-[#333] px-4 py-2 font-bold text-sm bg-black"><Activity size={16} className="text-primary"/> FAST</span>
                <span className="flex items-center gap-2 border-2 border-[#333] px-4 py-2 font-bold text-sm bg-black"><Layers size={16} className="text-yellow-400"/> DISTRIBUTED</span>
              </div>
            </div>
          </div>

          <div className="flex-1 w-full max-w-md relative">
            <div className="absolute -bottom-8 -right-8 w-32 h-32 bg-danger z-0"></div>
            <div className="bg-[#111] border-4 border-white p-8 relative z-10 shadow-[8px_8px_0px_rgba(255,255,255,0.1)]">
              <div className="text-center mb-6">
                <UploadCloud size={48} className="mx-auto mb-4 text-white" />
                <h2 className="text-2xl font-black tracking-tight">UPLOAD TASK</h2>
                <p className="text-sm text-gray-400 mt-2">Select an image to process asynchronously</p>
              </div>

              <form onSubmit={handleUpload} className="space-y-4">
                <div className="border-2 border-dashed border-[#555] p-4 text-center hover:border-primary transition-colors cursor-pointer relative overflow-hidden bg-black">
                  <input 
                    type="file" 
                    onChange={(e) => setFile(e.target.files[0])} 
                    accept="image/*" 
                    required={!activeJob}
                    className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                  />
                  <span className="text-sm font-bold text-gray-300">
                    {file ? file.name : "CLICK TO BROWSE"}
                  </span>
                </div>
                
                <div className="grid grid-cols-2 gap-4">
                  <select value={opType} onChange={e => setOpType(e.target.value)} className="col-span-2 bg-black border-2 border-[#333] p-3 text-sm font-bold uppercase focus:border-primary outline-none">
                    <option value="resize">RESIZE</option>
                    <option value="format_convert">CONVERT</option>
                  </select>

                  {opType === 'resize' ? (
                    <>
                      <input type="number" placeholder="W" value={width} onChange={e => setWidth(e.target.value)} className="bg-black border-2 border-[#333] p-3 text-sm font-bold uppercase focus:border-primary outline-none" />
                      <input type="number" placeholder="H" value={height} onChange={e => setHeight(e.target.value)} className="bg-black border-2 border-[#333] p-3 text-sm font-bold uppercase focus:border-primary outline-none" />
                    </>
                  ) : (
                    <select value={format} onChange={e => setFormat(e.target.value)} className="col-span-2 bg-black border-2 border-[#333] p-3 text-sm font-bold uppercase focus:border-primary outline-none">
                      <option value="webp">WEBP</option>
                      <option value="png">PNG</option>
                      <option value="jpg">JPG</option>
                    </select>
                  )}
                </div>

                <button 
                  type="submit" 
                  disabled={uploading || !file}
                  className="w-full bg-yellow-400 text-black font-black uppercase py-4 border-2 border-black hover:bg-yellow-300 transition-colors mt-4 disabled:opacity-50"
                >
                  {uploading ? 'UPLOADING...' : 'START PROCESSING'}
                </button>
                
                <div className="flex justify-between text-[10px] text-gray-500 font-bold uppercase pt-4 border-t border-[#333] mt-4">
                  <span>MAX SIZE: 5MB</span>
                  <span>FORMATS: JPG, PNG, WEBP</span>
                </div>
              </form>
            </div>
          </div>
        </section>

        {/* Process Timeline Section */}
        {activeJob && (
          <section className="px-8 py-10 border-t-4 border-[#333] bg-[#111]">
            <div className="max-w-4xl mx-auto border-4 border-white p-8 bg-[#0a0a0a] shadow-[8px_8px_0px_rgba(255,255,255,0.1)]">
              <h3 className="text-2xl font-black tracking-tight mb-6 flex items-center gap-3">
                {getStatusIcon(activeJob.status)} 
                TASK STATUS: <span className="text-primary uppercase">{activeJob.status}</span>
              </h3>
              
              <div className="relative pt-4">
                <div className="overflow-hidden h-2 mb-4 text-xs flex rounded bg-[#333]">
                  <div style={{ width: activeJob.status === 'completed' ? '100%' : activeJob.status === 'failed' ? '100%' : activeJob.status === 'processing' ? '66%' : '33%' }} className={`shadow-none flex flex-col text-center whitespace-nowrap text-white justify-center ${activeJob.status === 'failed' ? 'bg-danger' : 'bg-primary animate-pulse'}`}></div>
                </div>
                <div className="flex justify-between text-xs font-bold text-gray-400 uppercase">
                  <span className={activeJob.status !== 'pending' ? 'text-white' : ''}>Queued</span>
                  <span className={activeJob.status === 'processing' || activeJob.status === 'completed' ? 'text-white' : ''}>Processing</span>
                  <span className={activeJob.status === 'completed' ? 'text-success' : activeJob.status === 'failed' ? 'text-danger' : ''}>Finished</span>
                </div>
              </div>

              {activeJob.status === 'completed' && activeJob.result_path && (
                <div className="mt-8 flex justify-center">
                  <a href={`${API_BASE}/storage/results/${activeJob.result_path.split(/[\\/]/).pop()}`} download target="_blank" rel="noreferrer" className="w-full max-w-sm bg-success hover:bg-green-400 text-slate-900 font-black py-4 border-2 border-black transition-colors flex items-center justify-center gap-2 shadow-[4px_4px_0px_#16a34a] uppercase">
                    <Download size={24} /> Download Result Image
                  </a>
                </div>
              )}
              
              {activeJob.status === 'failed' && (
                <div className="mt-8 p-4 bg-danger/20 border-2 border-danger text-danger font-mono text-sm">
                  Error: {activeJob.error_message || 'Unknown processing error occurred.'}
                </div>
              )}
            </div>
          </section>
        )}

        <section id="network" className="px-8 py-20 border-t-4 border-[#333] bg-black">
          <div className="max-w-7xl mx-auto">
            <div className="mb-12">
              <h2 className="text-4xl md:text-5xl font-black uppercase tracking-tighter">NETWORK ARCHITECTURE</h2>
              <p className="text-gray-400 mt-2 font-medium">Distributed Processing Pipeline</p>
            </div>
            
            <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
              <div className="space-y-6">
                <div className="border-2 border-white p-4 bg-[#111]">
                  <div className="text-[10px] text-gray-500 font-bold uppercase mb-2">CURRENT STATUS</div>
                  <div className="text-xl font-black flex items-center gap-2"><span className="w-3 h-3 bg-yellow-400 rounded-full animate-pulse"></span> PROCESSING</div>
                </div>
                <div className="border-2 border-white p-4 bg-[#111]">
                  <div className="text-[10px] text-gray-500 font-bold uppercase mb-2">NODES ACTIVE</div>
                  <div className="text-xl font-black flex items-center gap-2"><Server className="text-primary"/> MULTIPLE</div>
                </div>
              </div>

              <div className="lg:col-span-3 border-4 border-white bg-[#0a0a0a] p-8 relative min-h-[400px] flex items-center justify-center overflow-hidden shadow-[8px_8px_0px_#333]">
                <svg className="absolute inset-0 w-full h-full z-0" pointerEvents="none">
                  <path d="M150,200 L300,200 L300,100 L450,100" stroke="#38bdf8" strokeWidth="4" fill="none" strokeDasharray="5,5" className="animate-[dash_2s_linear_infinite]" />
                  <path d="M150,200 L300,200 L300,300 L450,300" stroke="#38bdf8" strokeWidth="4" fill="none" strokeDasharray="5,5" className="animate-[dash_2s_linear_infinite]" />
                  <path d="M150,200 L300,200 L450,200" stroke="#38bdf8" strokeWidth="4" fill="none" strokeDasharray="5,5" className="animate-[dash_2s_linear_infinite]" />
                  
                  <path d="M650,100 L800,100 L800,200 L950,200" stroke="#4ade80" strokeWidth="4" fill="none" strokeDasharray="5,5" className="animate-[dash_2s_linear_infinite_reverse]" />
                  <path d="M650,200 L950,200" stroke="#4ade80" strokeWidth="4" fill="none" strokeDasharray="5,5" className="animate-[dash_2s_linear_infinite_reverse]" />
                  <path d="M650,300 L800,300 L800,200 L950,200" stroke="#4ade80" strokeWidth="4" fill="none" strokeDasharray="5,5" className="animate-[dash_2s_linear_infinite_reverse]" />
                </svg>

                <div className="relative z-10 w-full flex justify-between items-center">
                  <div className="w-48 bg-white text-black border-4 border-black p-4 text-center z-10 relative">
                    <Monitor size={32} className="mx-auto mb-2" />
                    <div className="font-black text-xl tracking-tight">API HUB</div>
                    <div className="text-[10px] font-bold mt-1 bg-black text-white px-2 py-1 inline-block">FASTAPI</div>
                  </div>

                  <div className="flex flex-col gap-8 z-10">
                    <div className="w-48 bg-[#1a1a1a] border-4 border-primary p-4 text-center flex flex-col items-center">
                       <RefreshCw size={24} className="text-primary animate-spin-slow mb-2" />
                       <div className="font-black tracking-tight text-white">WORKER 1</div>
                       <div className="text-xs text-primary font-bold">RESIZE OP</div>
                    </div>
                    <div className="w-48 bg-[#1a1a1a] border-4 border-primary p-4 text-center flex flex-col items-center">
                       <RefreshCw size={24} className="text-primary animate-spin-slow mb-2" />
                       <div className="font-black tracking-tight text-white">WORKER 2</div>
                       <div className="text-xs text-primary font-bold">CONVERT OP</div>
                    </div>
                    <div className="w-48 bg-[#1a1a1a] border-4 border-primary p-4 text-center flex flex-col items-center">
                       <RefreshCw size={24} className="text-primary animate-spin-slow mb-2" />
                       <div className="font-black tracking-tight text-white">WORKER 3</div>
                       <div className="text-xs text-primary font-bold">DLQ HANDLER</div>
                    </div>
                  </div>

                  <div className="w-48 bg-black border-4 border-success p-4 text-center z-10 relative">
                    <Database size={32} className="mx-auto mb-2 text-success" />
                    <div className="font-black text-xl tracking-tight text-white">DATA TIER</div>
                    <div className="text-[10px] font-bold mt-1 bg-success text-black px-2 py-1 inline-block">POSTGRES & REDIS</div>
                  </div>

                </div>
                
                <div className="absolute bottom-4 right-4 bg-yellow-400 text-black text-[10px] font-black px-3 py-1 flex items-center gap-2">
                  <span className="w-2 h-2 bg-black rounded-full animate-ping"></span> LIVE SYNC
                </div>
              </div>
            </div>
            
            <div className="mt-8 bg-[#0a0a0a] border-4 border-[#333] p-4 font-mono text-xs text-gray-400 h-40 overflow-hidden">
              <div className="flex items-center gap-2 text-gray-500 mb-2 border-b border-[#333] pb-2">
                <HardDrive size={14} /> SYSTEM LOG
              </div>
              <div className="space-y-1">
                <div><span className="text-primary">[10:42:01]</span> Hub received payload</div>
                <div><span className="text-primary">[10:42:02]</span> Distributing to Worker Node pool</div>
                <div><span className="text-yellow-400">[10:42:05]</span> Processing complete. Analyzing storage allocation...</div>
                <div><span className="text-success">[10:42:08]</span> Result saved successfully to database.</div>
              </div>
            </div>

          </div>
        </section>
      </main>

      <footer className="bg-black border-t border-[#333] p-8 flex justify-between items-center text-xs font-bold text-gray-600 uppercase tracking-widest">
        <div>IMAGEFLOW</div>
        <div>© 2026 IMAGEFLOW. FORM FOLLOWS FUNCTION.</div>
      </footer>
      
      <style>{`
        @keyframes dash {
          to {
            stroke-dashoffset: -20;
          }
        }
        @keyframes dash_reverse {
          to {
            stroke-dashoffset: 20;
          }
        }
        .animate-spin-slow {
          animation: spin 3s linear infinite;
        }
      `}</style>
    </div>
  );
};

export default LandingPage;
