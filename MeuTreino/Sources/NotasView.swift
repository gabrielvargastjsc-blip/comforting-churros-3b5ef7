import SwiftUI
import SwiftData

// Suas anotações livres (o "diário" de observações).
struct NotasView: View {
    @Environment(\.modelContext) private var context
    @Query(sort: \Nota.data, order: .reverse) private var notas: [Nota]

    var body: some View {
        NavigationStack {
            List {
                ForEach(notas) { nota in
                    NavigationLink {
                        NotaEditor(nota: nota)
                    } label: {
                        VStack(alignment: .leading, spacing: 2) {
                            Text(nota.texto.isEmpty ? "(vazia)" : nota.texto).lineLimit(2)
                            Text(nota.data, style: .date)
                                .font(.caption).foregroundStyle(.secondary)
                        }
                    }
                }
                .onDelete(perform: apagar)
            }
            .navigationTitle("Notas")
            .toolbar {
                ToolbarItem(placement: .primaryAction) {
                    Button(action: adicionar) { Image(systemName: "plus") }
                }
            }
            .overlay {
                if notas.isEmpty {
                    ContentUnavailableView("Sem notas",
                                           systemImage: "note.text",
                                           description: Text("Toque em + para escrever."))
                }
            }
        }
    }

    private func adicionar() {
        context.insert(Nota(texto: ""))
    }

    private func apagar(_ offsets: IndexSet) {
        for i in offsets { context.delete(notas[i]) }
    }
}

struct NotaEditor: View {
    @Bindable var nota: Nota

    var body: some View {
        Form {
            DatePicker("Data", selection: $nota.data, displayedComponents: .date)
            TextField("Escreva aqui...", text: $nota.texto, axis: .vertical)
                .frame(minHeight: 120, alignment: .topLeading)
        }
        .navigationTitle("Nota")
        .navigationBarTitleDisplayMode(.inline)
    }
}
