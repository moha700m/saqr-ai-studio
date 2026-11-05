import { Route, Routes } from 'react-router-dom';
import Layout from './components/Layout';
import { BridgeProvider } from './lib/bridge-context';
import Dashboard from './pages/Dashboard';
import Docs from './pages/Docs';
import Downloads from './pages/Downloads';
import Hardware from './pages/Hardware';
import ImageStudio from './pages/ImageStudio';
import Landing from './pages/Landing';
import Live from './pages/Live';
import Models from './pages/Models';
import Privacy from './pages/Privacy';
import Settings from './pages/Settings';
import Studio from './pages/Studio';
import VideoStudio from './pages/VideoStudio';

export default function App() {
  return (
    <BridgeProvider>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route element={<Layout />}>
          <Route path="/app" element={<Dashboard />} />
          <Route path="/studio" element={<Studio />} />
          <Route path="/live" element={<Live />} />
          <Route path="/image" element={<ImageStudio />} />
          <Route path="/video" element={<VideoStudio />} />
          <Route path="/models" element={<Models />} />
          <Route path="/hardware" element={<Hardware />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="/downloads" element={<Downloads />} />
          <Route path="/docs" element={<Docs />} />
          <Route path="/privacy" element={<Privacy />} />
        </Route>
        <Route path="*" element={<Landing />} />
      </Routes>
    </BridgeProvider>
  );
}
