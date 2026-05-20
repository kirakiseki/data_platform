<script setup lang="ts">
defineOptions({
  name: 'IndexPage',
})

const router = useRouter()
onMounted(() => {
  router.push('/dashboard')
})
</script>

<template>
  <div>
    <p>加载中...</p>
  </div>
</template>
