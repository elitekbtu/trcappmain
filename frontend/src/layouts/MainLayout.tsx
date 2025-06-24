import { Outlet } from 'react-router-dom'
import MainNavbar from '../components/Main/Navbar'
import MainFooter from '../components/Main/Footer'

const MainLayout = () => {
  return (
    <div className="flex min-h-screen flex-col">
      <MainNavbar />
      <main className="flex-1 bg-muted/30 py-6">
        <Outlet />
      </main>
      <MainFooter />
    </div>
  )
}

export default MainLayout