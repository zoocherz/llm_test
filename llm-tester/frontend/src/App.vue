<template>
  <div id="app">
    <el-container class="layout-container">
      <el-header class="main-header">
        <h1>LLM Tester</h1>
        <el-menu mode="horizontal" :ellipsis="false" :default-active="activeSection" router>
          <el-menu-item index="/">Главная</el-menu-item>
          <el-menu-item index="/datasets">Датасеты</el-menu-item>
          <el-menu-item index="/models">Модели</el-menu-item>
          <el-menu-item index="/experiments">Эксперименты</el-menu-item>
          <el-menu-item index="/runs">Запуски</el-menu-item>
        </el-menu>
      </el-header>
      <el-main><router-view /></el-main>
      <el-footer>LLM Prompt &amp; Model Testing Tool © 2024</el-footer>
    </el-container>
  </div>
</template>
<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
const route = useRoute()
const activeSection = computed(() => route.path === '/' ? '/' : '/' + route.path.split('/')[1])
</script>
<style>
#app{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Oxygen,Ubuntu,sans-serif}.layout-container{min-height:100vh}.main-header{display:flex;align-items:center;justify-content:space-between;background-color:#409EFF;color:white}.main-header h1{margin:0;font-size:24px}.main-header .el-menu{background-color:transparent;border:none}.main-header .el-menu-item{color:white}.main-header .el-menu-item:hover,.main-header .el-menu-item.is-active{color:#fff;background-color:rgba(0,0,0,.24);border-bottom:2px solid #fff}.el-main{padding:20px;background-color:#f5f7fa}.el-footer{text-align:center;color:#666;font-size:14px}
</style>
