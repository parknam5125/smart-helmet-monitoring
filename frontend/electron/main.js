const { app, BrowserWindow, Menu, Tray, nativeImage } = require('electron')
const path = require('path')
const { spawn } = require('child_process')

let mainWindow
let tray
let nextProcess

const isDev = process.env.NODE_ENV === 'development'

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1000,
    minHeight: 700,
    backgroundColor: '#0f0f14',
    titleBarStyle: 'hiddenInset',
    frame: process.platform === 'darwin' ? true : false,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js')
    },
    icon: path.join(__dirname, '../public/icon.png')
  })

  // Custom title bar for Windows/Linux
  if (process.platform !== 'darwin') {
    mainWindow.setMenuBarVisibility(false)
  }

  const startUrl = isDev 
    ? 'http://localhost:3000' 
    : `file://${path.join(__dirname, '../out/index.html')}`

  mainWindow.loadURL(startUrl)

  mainWindow.on('closed', () => {
    mainWindow = null
  })

  // Open DevTools in development
  if (isDev) {
    mainWindow.webContents.openDevTools()
  }
}

function createTray() {
  const icon = nativeImage.createFromPath(path.join(__dirname, '../public/icon.png'))
  tray = new Tray(icon.resize({ width: 16, height: 16 }))
  
  const contextMenu = Menu.buildFromTemplate([
    { 
      label: 'Show Dashboard', 
      click: () => {
        if (mainWindow) {
          mainWindow.show()
          mainWindow.focus()
        }
      }
    },
    { type: 'separator' },
    { 
      label: 'Quit', 
      click: () => {
        app.quit()
      }
    }
  ])
  
  tray.setToolTip('Smart Helmet Monitor')
  tray.setContextMenu(contextMenu)
  
  tray.on('click', () => {
    if (mainWindow) {
      mainWindow.isVisible() ? mainWindow.hide() : mainWindow.show()
    }
  })
}

function startNextServer() {
  if (isDev) {
    nextProcess = spawn('npm', ['run', 'dev'], {
      cwd: path.join(__dirname, '..'),
      shell: true
    })

    nextProcess.stdout.on('data', (data) => {
      console.log(`Next.js: ${data}`)
    })

    nextProcess.stderr.on('data', (data) => {
      console.error(`Next.js Error: ${data}`)
    })
  }
}

app.whenReady().then(() => {
  if (isDev) {
    startNextServer()
    // Wait for Next.js server to start
    setTimeout(() => {
      createWindow()
      createTray()
    }, 5000)
  } else {
    createWindow()
    createTray()
  }

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow()
    }
  })
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit()
  }
})

app.on('before-quit', () => {
  if (nextProcess) {
    nextProcess.kill()
  }
})

// Handle creating/removing shortcuts on Windows when installing/uninstalling.
if (require('electron-squirrel-startup')) {
  app.quit()
}
