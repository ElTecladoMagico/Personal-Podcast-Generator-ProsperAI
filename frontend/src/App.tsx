import { Show, SignInButton, UserButton } from '@clerk/react'

export default function App() {
  return (
    <main className="grid min-h-svh place-items-center gap-4">
      <h1 className="text-5xl">Personal Podcast</h1>
      <Show when="signed-out">
        <SignInButton />
      </Show>
      <Show when="signed-in">
        <UserButton />
      </Show>
    </main>
  )
}
