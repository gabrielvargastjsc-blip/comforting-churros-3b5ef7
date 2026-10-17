import SwiftUI
import SwiftData

// Ponto de entrada do app. Cria o banco local (SwiftData) com os seus modelos.
// Todos os dados ficam no seu iPhone, na sua conta — nada vai para servidor nenhum.
@main
struct MeuTreinoApp: App {
    var body: some Scene {
        WindowGroup {
            RootView()
        }
        .modelContainer(for: [Treino.self, Exercicio.self, Serie.self, Nota.self])
    }
}
