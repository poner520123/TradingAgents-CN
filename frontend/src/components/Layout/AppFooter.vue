<template>
  <div class="app-footer">
    <div class="footer-content">
      <div class="copyright">
        <span>© 2025 TA v1.0.0-preview</span>
        <span class="rights">All rights reserved.</span>
      </div>
      <div class="disclaimer-text">
        TA 是 AI 股票分析辅助工具，不构成投资建议。市场有风险，投资需谨慎。
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
// Footer组件逻辑
</script>

<style lang="scss" scoped>
.app-footer {
  .footer-content {
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    gap: 6px;
    color: var(--el-text-color-regular);
    font-size: 14px;
    padding: 12px 16px;
    text-align: center;
  }

  .rights {
    margin-left: 4px;
  }

  .disclaimer-text {
    color: var(--el-text-color-secondary);
    font-size: 12px;
    line-height: 1.6;
    max-width: 1100px;
  }
}
</style>

