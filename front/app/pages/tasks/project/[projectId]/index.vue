<template>
  <TaskWorkspaceShell
    v-if="allowed"
    section="project"
    :project-id="projectId"
  />
  <ContainerWrapper
    v-else-if="store.loaded"
    dir="rtl"
    class="py-8"
  >
    <Card class="p-8 text-center shadow-none">
      <p class="text-sm text-muted-foreground">
        این کارتابل واحد پیدا نشد یا به واحد شما مربوط نیست.
      </p>
      <Button
        class="mt-4"
        @click="navigateTo('/tasks/project')"
      >
        بازگشت به کارتابل واحد
      </Button>
    </Card>
  </ContainerWrapper>
</template>

<script setup lang="ts">
import TaskWorkspaceShell from '~/components/tasks/TaskWorkspaceShell.vue'
import { useTaskWorkspaceStore } from '~/stores/taskWorkspace'

const route = useRoute()
const store = useTaskWorkspaceStore()
const projectId = computed(() => String(route.params.projectId))

// The server already limits /tasks/meta to the user's own units (admins: all), so a project id
// that is not in that list is one the user has no access to -- typing its URL must not open it.
// Until the first load finishes the shell is shown (it loads the store itself).
const allowed = computed(() => !store.loaded || !!store.getProjectById(projectId.value))
onMounted(() => store.ensureLoaded())
</script>
