import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';

export default function Layout() {
  return (
    <div className="flex min-h-screen bg-eso-dark-950">
      <Sidebar />
      {/* Responsive: no margin on mobile, sidebar margin on medium+ screens */}
      <main className="flex-1 ml-0 md:ml-64">
        <div className="p-4 md:p-8">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
