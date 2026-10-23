/**
 * Vitest 独立配置。
 *
 * 为什么不用 vite.config.ts：
 * 1. vite.config.ts 中的 ViteImageOptimizer 插件会真的处理图片资源，测试环境下
 *    既慢又无意义；
 * 2. 测试需要独立的环境（happy-dom）、全局 setup、覆盖率配置；
 * 3. AutoImport / Components 插件必须保留 —— 业务代码（如 stores/auth.ts）依赖
 *    unplugin-auto-import 注入的 ElMessage 等 Element Plus 符号。
 *
 * 注意 dts 均设为 false，避免测试运行污染仓库中的自动生成声明文件。
 */
import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'
import AutoImport from 'unplugin-auto-import/vite'
import Components from 'unplugin-vue-components/vite'
import { ElementPlusResolver } from 'unplugin-vue-components/resolvers'

export default defineConfig({
  plugins: [
    vue(),
    AutoImport({
      resolvers: [ElementPlusResolver()],
      imports: ['vue', 'vue-router', 'pinia', '@vueuse/core'],
      dts: false,
      eslintrc: { enabled: false }
    }),
    Components({
      resolvers: [ElementPlusResolver()],
      dts: false
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
  test: {
    environment: 'happy-dom',
    globals: true,
    setupFiles: ['./src/__tests__/setup.ts'],
    include: ['src/**/*.{test,spec}.{ts,tsx}'],
    exclude: ['node_modules/**', 'dist/**'],
    // 后端接口契约测试较慢（涉及真实模块导入），放宽超时
    testTimeout: 20000,
    hookTimeout: 20000,
    restoreMocks: true,
    clearMocks: true,
    server: {
      deps: {
        // element-plus 的 ESM 产物会 import .css，Node 加载器无法直接处理，
        // 交给 Vite 管线处理即可。
        inline: ['element-plus']
      }
    },
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html'],
      include: ['src/utils/**', 'src/api/**', 'src/stores/**'],
      exclude: ['src/**/__tests__/**']
    }
  }
})
