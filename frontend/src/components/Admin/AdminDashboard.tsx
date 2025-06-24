import { motion } from 'framer-motion'
import { Outlet, Link, useLocation } from 'react-router-dom'
import { Users, Shirt, Layers, ChevronRight } from 'lucide-react'
import { cn } from '../../lib/utils'

const AdminDashboard = () => {
  const location = useLocation()
  const currentPath = location.pathname

  const navItems = [
    {
      path: '/admin/users',
      label: 'Пользователи',
      icon: <Users className="h-4 w-4" />
    },
    {
      path: '/admin/items',
      label: 'Товары',
      icon: <Shirt className="h-4 w-4" />
    },
    {
      path: '/admin/outfits',
      label: 'Образы',
      icon: <Layers className="h-4 w-4" />
    }
  ]

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1
      }
    }
  }

  const itemVariants = {
    hidden: { opacity: 0, y: 10 },
    visible: { opacity: 1, y: 0 }
  }

  return (
    <motion.div
      initial="hidden"
      animate="visible"
      variants={containerVariants}
      className="min-h-screen bg-muted/40"
    >
      <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <motion.div variants={itemVariants} className="mb-8">
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Link to="/home" className="hover:text-primary hover:underline">
              Главная
            </Link>
            <ChevronRight className="h-4 w-4" />
            <span className="text-foreground">Админ панель</span>
          </div>
          <h1 className="mt-2 font-display text-3xl font-bold tracking-tight">Административная панель</h1>
          <p className="text-muted-foreground">Управление контентом и пользователями системы</p>
        </motion.div>

        {/* Navigation */}
        <motion.nav
          variants={itemVariants}
          className="mb-8 flex gap-1 rounded-lg bg-background p-1 shadow-sm"
        >
          {navItems.map((item) => (
            <Link
              key={item.path}
              to={item.path}
              className={cn(
                'flex items-center gap-2 rounded-md px-4 py-2 text-sm font-medium transition-all',
                currentPath.startsWith(item.path)
                  ? 'bg-primary text-primary-foreground shadow'
                  : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
              )}
            >
              {item.icon}
              {item.label}
            </Link>
          ))}
        </motion.nav>

        {/* Content */}
        <motion.div variants={itemVariants} className="rounded-lg bg-background p-6 shadow-sm">
          <Outlet />
        </motion.div>
      </div>
    </motion.div>
  )
}

export default AdminDashboard