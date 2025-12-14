import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'
import AutoImport from 'unplugin-auto-import/vite'
import Components from 'unplugin-vue-components/vite'
import { ElementPlusResolver } from 'unplugin-vue-components/resolvers'
import { ViteImageOptimizer } from 'vite-plugin-image-optimizer'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    AutoImport({
      resolvers: [ElementPlusResolver()],
      imports: [
        'vue',
        'vue-router',
        'pinia',
        '@vueuse/core'
      ],
      dts: true,
      eslintrc: {
        enabled: true
      }
    }),
    // 自动按需组件导入
    Components({
      resolvers: [ElementPlusResolver()],
      dts: true
    }),
    // 图片资源优化插件
    ViteImageOptimizer({
      // 配置 PNG 优化
      png: {
        quality: 80,
        compressionLevel: 6,
      },
      // 配置 JPEG 优化
      jpeg: {
        quality: 80,
      },
      // 配置 WebP 转换
      webp: {
        quality: 80,
      },
      // 配置 AVIF 转换（可选）
      avif: {
        quality: 80,
      },
      // 配置 SVG 优化
      svg: {
        multipass: true,
        plugins: [
          {
            name: 'preset-default',
            params: {
              overrides: {
                removeViewBox: false,
              },
            },
          },
        ],
      },
      // 输出优化后的图片到 dist 目录
      includePublic: true,
      // 仅在生产构建时运行
      disable: false,
    })
  ],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
      '@components': resolve(__dirname, 'src/components'),
      '@views': resolve(__dirname, 'src/views'),
      '@stores': resolve(__dirname, 'src/stores'),
      '@utils': resolve(__dirname, 'src/utils'),
      '@types': resolve(__dirname, 'src/types'),
      '@api': resolve(__dirname, 'src/api')
    }
  },
  server: {
    host: '0.0.0.0',
    port: 3000,
    hmr: {
      overlay: false
    },
    // 允许从项目根目录之外（例如 /docs）导入原始文件
    fs: {
      allow: [resolve(__dirname, '..')]
    },
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
        ws: true  // 🔥 启用 WebSocket 代理支持
      }
    }
  },
  build: {
    target: 'es2020',  // 支持 nullish coalescing operator (??) 和 optional chaining (?.)
    outDir: 'dist',
    assetsDir: 'assets',
    sourcemap: false,
    rollupOptions: {
      output: {
        chunkFileNames: 'js/[name]-[hash].js',
        entryFileNames: 'js/[name]-[hash].js',
        assetFileNames: '[ext]/[name]-[hash].[ext]',
        // 代码分割策略：
        // 1. 将 node_modules 中的第三方库单独打包
        // 2. 将组件按页面/功能模块分割
        // 3. 将工具函数和公共组件单独打包
        manualChunks: {
          // 第三方库打包
          'vue-vendor': ['vue', 'vue-router', 'pinia'],
          'element-plus': ['element-plus'],
          'echarts': ['echarts'],
          'axios': ['axios'],
          // 功能模块打包
          'analysis': ['@/views/Analysis/SingleAnalysis.vue', '@/views/Analysis/BatchAnalysis.vue', '@/views/Analysis/CrawlerAnalysis.vue'],
          'reports': ['@/views/Reports/index.vue', '@/views/Reports/ReportDetail.vue', '@/views/Reports/TokenStatistics.vue'],
          'settings': ['@/views/Settings/index.vue', '@/views/Settings/ConfigManagement.vue'],
          // 系统管理模块
          'system': ['@/views/System/DatabaseManagement.vue', '@/views/System/LogManagement.vue', '@/views/System/MultiSourceSync.vue']
        }
      }
    }
  },
  css: {
    preprocessorOptions: {
      scss: {
        additionalData: `@use "@/styles/variables.scss" as *;`
      }
    }
  }
})
