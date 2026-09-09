<template>
  <div id="app">
    <el-container class="layout-container">
      <el-header class="main-header">
        <h1>LLM Tester</h1>
        <el-menu mode="horizontal" :ellipsis="false" router>
          <el-menu-item index="/providers">Providers</el-menu-item>
          <el-menu-item index="/tasks">Tasks</el-menu-item>
          <el-menu-item index="/runs">Test Runs</el-menu-item>
        </el-menu>
      </el-header>
      
      <el-main>
        <router-view />
      </el-main>
      
      <el-footer>
        LLM Prompt & Model Testing Tool © 2024
      </el-footer>
    </el-container>
  </div>
</template>

<script setup>
</script>

<style>
#app {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
}

.layout-container {
  min-height: 100vh;
}

.main-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background-color: #409EFF;
  color: white;
}

.main-header h1 {
  margin: 0;
  font-size: 24px;
}

.main-header .el-menu {
  background-color: transparent;
  border: none;
}

.main-header .el-menu-item {
  color: white;
}

.main-header .el-menu-item:hover {
  background-color: rgba(255, 255, 255, 0.2);
}

.el-main {
  padding: 20px;
  background-color: #f5f7fa;
}

.el-footer {
  text-align: center;
  color: #666;
  font-size: 14px;
}
</style>
