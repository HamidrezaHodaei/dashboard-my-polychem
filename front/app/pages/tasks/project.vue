<template>
  <NuxtPage v-if="route.params.projectId" />
  <TaskWorkspaceShell
    v-else
    section="project"
  />
</template>

<script setup lang="ts">
import TaskWorkspaceShell from '~/components/tasks/TaskWorkspaceShell.vue'

const route = useRoute()

usePageSeoMeta({ title: 'کارتابل واحد' })
</script>
