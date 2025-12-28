<template>
  <div class="global-notification">
    <div 
      v-for="notification in visibleNotifications" 
      :key="notification.id" 
      class="notification-item" 
      :class="notification.type"
      @click="handleNotificationClick(notification)"
    >
      <div class="notification-content">
        <div class="notification-header">
          <div class="notification-title">{{ notification.title }}</div>
          <div class="notification-time">{{ formatTime(notification.created_at) }}</div>
        </div>
        <div class="notification-body">{{ notification.content }}</div>
      </div>
      <div class="notification-close" @click.stop="closeNotification(notification.id)">
        <el-icon><Close /></el-icon>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useNotificationStore } from '@/stores/notifications'
import { Close } from '@element-plus/icons-vue'
import { useRouter } from 'vue-router'

const notificationStore = useNotificationStore()
const router = useRouter()

// 最多显示5个通知
const MAX_NOTIFICATIONS = 5

// 可见通知列表
const visibleNotifications = computed(() => {
  return notificationStore.items.slice(0, MAX_NOTIFICATIONS)
})

// 定时器映射
const timers = ref<Map<string, number>>(new Map())

// 格式化时间
const formatTime = (time: string) => {
  const date = new Date(time)
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  
  if (diff < 60000) {
    return '刚刚'
  } else if (diff < 3600000) {
    return `${Math.floor(diff / 60000)}分钟前`
  } else if (diff < 86400000) {
    return `${Math.floor(diff / 3600000)}小时前`
  } else {
    return `${Math.floor(diff / 86400000)}天前`
  }
}

// 关闭通知
const closeNotification = (id: string) => {
  // 清除定时器
  if (timers.value.has(id)) {
    clearTimeout(timers.value.get(id) as number)
    timers.value.delete(id)
  }
  
  // 从store中移除通知
  notificationStore.items = notificationStore.items.filter(item => item.id !== id)
}

// 点击通知
const handleNotificationClick = (notification: any) => {
  // 如果有链接，跳转到对应页面
  if (notification.link) {
    router.push(notification.link)
  }
  
  // 标记为已读
  notificationStore.markRead(notification.id)
}

// 设置自动关闭定时器
const setAutoCloseTimer = (id: string) => {
  // 5秒后自动关闭
  const timer = window.setTimeout(() => {
    closeNotification(id)
  }, 5000)
  timers.value.set(id, timer)
}

// 监听通知变化，设置自动关闭定时器
const watchNotifications = () => {
  const unwatch = notificationStore.$subscribe((mutation, state) => {
    if (mutation.events?.includes('items')) {
      // 为新通知设置自动关闭定时器
      const newNotifications = state.items.filter(item => !timers.value.has(item.id))
      newNotifications.forEach(notification => {
        setAutoCloseTimer(notification.id)
      })
    }
  })
  
  return unwatch
}

// 组件挂载时
onMounted(() => {
  // 为现有通知设置定时器
  notificationStore.items.forEach(notification => {
    setAutoCloseTimer(notification.id)
  })
  
  // 监听通知变化
  watchNotifications()
  
  // 连接WebSocket
  if (!notificationStore.wsConnected) {
    notificationStore.connect()
  }
})

// 组件卸载时
onUnmounted(() => {
  // 清除所有定时器
  timers.value.forEach(timer => {
    clearTimeout(timer)
  })
  timers.value.clear()
})
</script>

<style lang="scss" scoped>
.global-notification {
  position: fixed;
  top: 80px;
  right: 20px;
  z-index: 9999;
  display: flex;
  flex-direction: column;
  gap: 12px;
  
  .notification-item {
    position: relative;
    min-width: 300px;
    max-width: 400px;
    padding: 16px;
    border-radius: 8px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    background: #fff;
    cursor: pointer;
    transition: all 0.3s ease;
    animation: slideInRight 0.3s ease-out;
    
    &:hover {
      transform: translateY(-2px);
      box-shadow: 0 6px 16px rgba(0, 0, 0, 0.2);
    }
    
    &.success {
      border-left: 4px solid #67c23a;
      background: linear-gradient(135deg, #f0f9eb 0%, #ffffff 100%);
    }
    
    &.error {
      border-left: 4px solid #f56c6c;
      background: linear-gradient(135deg, #fef0f0 0%, #ffffff 100%);
    }
    
    &.warning {
      border-left: 4px solid #e6a23c;
      background: linear-gradient(135deg, #fdf6ec 0%, #ffffff 100%);
    }
    
    &.info {
      border-left: 4px solid #409eff;
      background: linear-gradient(135deg, #ecf5ff 0%, #ffffff 100%);
    }
    
    .notification-content {
      .notification-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 8px;
        
        .notification-title {
          font-size: 14px;
          font-weight: 600;
          color: #303133;
        }
        
        .notification-time {
          font-size: 12px;
          color: #909399;
        }
      }
      
      .notification-body {
        font-size: 13px;
        color: #606266;
        line-height: 1.5;
        overflow: hidden;
        text-overflow: ellipsis;
        display: -webkit-box;
        -webkit-line-clamp: 3;
        -webkit-box-orient: vertical;
      }
    }
    
    .notification-close {
      position: absolute;
      top: 12px;
      right: 12px;
      width: 20px;
      height: 20px;
      display: flex;
      align-items: center;
      justify-content: center;
      border-radius: 4px;
      cursor: pointer;
      color: #909399;
      transition: all 0.2s;
      
      &:hover {
        background: #f5f7fa;
        color: #606266;
      }
      
      &:active {
        background: #e4e7ed;
      }
    }
  }
}

// 滑入动画
@keyframes slideInRight {
  from {
    transform: translateX(100%);
    opacity: 0;
  }
  to {
    transform: translateX(0);
    opacity: 1;
  }
}
</style>
