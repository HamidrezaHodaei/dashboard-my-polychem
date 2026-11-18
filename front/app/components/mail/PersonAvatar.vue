<!--/components/mail/PersonAvatar.vue → <MailPersonAvatar /> : profile photo from users.avatar_data, initials otherwise -->
<script setup lang="ts">
import type { MailPerson } from '~/utils/mail'

defineProps<{ person?: Pick<MailPerson, 'full_name' | 'avatar'> | null, size?: string }>()
</script>

<template>
  <Avatar :class="[size || 'size-9', 'shrink-0']">
    <AvatarImage v-if="person?.avatar" :src="person.avatar" :alt="person.full_name" />
    <AvatarFallback class="bg-muted text-xs text-muted-foreground">
      {{ mailInitials(person?.full_name || '؟') }}
    </AvatarFallback>
  </Avatar>
</template>
